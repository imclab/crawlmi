from twisted.internet import reactor

from crawlmi import log, signals
from crawlmi.core.downloader import Downloader
from crawlmi.http.request import Request
from crawlmi.http.response import Response
from crawlmi.middleware.extension_manager import ExtensionManager
from crawlmi.middleware.pipeline_manager import PipelineManager
from crawlmi.queue import PriorityQueue, MemoryQueue
from crawlmi.settings import Settings
from crawlmi.signal_manager import SignalManager
from crawlmi.utils.defer import LoopingCall, defer_result
from crawlmi.utils.misc import arg_to_iter, load_object


class Engine(object):
    '''
    WARNING: don't stop() and start() engine. Use pause() and unpause(),
    instead.
    '''

    # how many seconds to wait between the checks of outq
    QUEUE_CHECK_FREQUENCY = 0.1

    def __init__(self, spider, user_settings=None, custom_settings=None,
                 clock=None):
        '''Constructor of Engine should be very lightweight, so that things
        can be easily unittested. For any more complicated initialization
        use `setup()`.
        '''
        self.spider = spider

        # initialize settings
        # 1. Crawlmi default settings
        self.settings = Settings.from_module(
            'crawlmi.settings.default_settings')
        # 2. user settings (e.g. from settings module)
        if user_settings:
            self.settings.update(user_settings)
        # 3. spider-specific settings
        self.settings.update(spider.settings)
        # 4. custom settings (e.g. from command line)
        if custom_settings:
            self.settings.update(custom_settings)

        self.running = False
        self.paused = False
        # clock is used in unittests
        self.clock = clock or reactor
        self.processing = LoopingCall(self._process_queue, clock=self.clock)

    def setup(self):
        # IMPORTANT: order of the following initializations is very important
        # so please, think twice about any changes to it

        # initialize logging
        if self.settings.get_bool('LOG_ENABLED'):
            log.start(
                self.settings['LOG_FILE'],
                self.settings['LOG_LEVEL'],
                self.settings['LOG_STDOUT'],
                self.settings['LOG_ENCODING'])

        # initialize signals
        self.signals = SignalManager(self)

        #initialize stats
        stats_cls = load_object(self.settings.get('STATS_CLASS'))
        self.stats = stats_cls(self)

        # initialize downloader
        self.inq = PriorityQueue(lambda _: MemoryQueue())
        self.outq = MemoryQueue()
        self.downloader = Downloader(self.settings, self.inq, self.outq,
                                     clock=self.clock)

        # initialize extensions
        self.extensions = ExtensionManager(self)
        # initialize downloader pipeline
        self.pipeline = PipelineManager(self)

    def start(self):
        self.running = True
        self.signals.send(signal=signals.engine_started)
        self.processing.schedule(self.QUEUE_CHECK_FREQUENCY)

    def stop(self, reason):
        self.signals.send(signal=signals.engine_stopping)
        self.running = False
        self.processing.cancel()
        self.downloader.close()
        self.inq.close()
        self.outq.close()
        log.msg(format='Engine stopped (%(reason)s)', reason=reason)
        self.stats.dump_stats()
        self.signals.send(signal=signals.engine_stopped)

    def pause(self):
        self.paused = True
        self.processing.schedule(5)

    def unpause(self):
        self.paused = False
        self.processing.schedule(self.QUEUE_CHECK_FREQUENCY)

    def download(self, request):
        '''"Download" the given request. First pass it through the downloader
        pipeline.
            - if the request is received from the pipeline, push it to inq
            - if the response is received from the pipeline, push it to outq
        '''
        request_or_response = self.pipeline.process_request(request)
        if request_or_response is None:
            return

        if isinstance(request_or_response, Request):
            self.signals.send(signal=signals.request_received,
                              request=request_or_response)
            self.inq.push(request_or_response)
        elif isinstance(request_or_response, Response):
            request_or_response.request = request
            self.outq.push(request_or_response)

    def _process_queue(self):
        while self.running and not self.paused and self.outq:
            response = self.outq.pop()
            self.signals.send(signal=signals.response_downloaded,
                              response=response)
            result = self.pipeline.process_response(response)
            if result is None:
                continue
            elif isinstance(result, Request):
                self.download(result)
                continue

            request = result.request

            dfd = defer_result(result)
            dfd.addCallback(self.signals.send,
                            signal=signals.response_received,
                            response=result)
            dfd.addCallbacks(request.callback, request.errback)
            dfd.addCallbacks(self._handle_spider_output,
                             self._handle_spider_error)

    def _handle_spider_output(self, result):
        pass

    def _handle_spider_error(self, failure):
        pass