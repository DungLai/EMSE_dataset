import logging
from multiprocessing import JoinableQueue, Process
from queue import Empty

from fonduer.meta import Meta, new_sessionmaker
from fonduer.utils import ProgressBar

QUEUE_TIMEOUT = 3

# Grab pointer to global metadata
_meta = Meta.init()


class UDFRunner(object):
    """
    Class to run UDFs in parallel using simple queue-based multiprocessing
    setup.
    """

    def __init__(self, udf_class, **udf_init_kwargs):
        self.logger = logging.getLogger(__name__)
        self.udf_class = udf_class
        self.udf_init_kwargs = udf_init_kwargs
        self.udfs = []

    def apply(
        self, xs, clear=True, parallelism=None, progress_bar=True, count=None, **kwargs
    ):
        """
        Apply the given UDF to the set of objects xs, either single or
        multi-threaded, and optionally calling clear() first.
        """
        # Clear everything downstream of this UDF if requested
        if clear:
            self.logger.info("Clearing existing...")
            Session = new_sessionmaker()
            session = Session()
            self.clear(session, **kwargs)
            session.commit()
            session.close()

        # Execute the UDF
        self.logger.info("Running UDF...")
        if parallelism is None or parallelism < 2:
            self.apply_st(xs, progress_bar, clear=clear, count=count, **kwargs)
        else:
            self.apply_mt(xs, parallelism, clear=clear, **kwargs)

    def clear(self, session, **kwargs):
        raise NotImplementedError()

    def apply_st(self, xs, progress_bar, count, **kwargs):
        """Run the UDF single-threaded, optionally with progress bar"""
        udf = self.udf_class(**self.udf_init_kwargs)

        # Set up ProgressBar if possible
        pb = None
        if progress_bar and hasattr(xs, "__len__") or count is not None:
            n = count if count is not None else len(xs)
            pb = ProgressBar(n)

        # Run single-thread
        for i, x in enumerate(xs):
            if pb:
                pb.bar(i)

            udf.session.add_all(y for y in udf.apply(x, **kwargs))

        # Commit session and close progress bar if applicable
        udf.session.commit()
        if pb:
            pb.close()

    def apply_mt(self, xs, parallelism, **kwargs):
        """Run the UDF multi-threaded using python multiprocessing"""
        if not _meta.postgres:
            raise ValueError("Fonduer must use PostgreSQL as a database backend.")

        # Fill a JoinableQueue with input objects
        in_queue = JoinableQueue()
        for x in xs:
            in_queue.put(x)

        # Start UDF Processes
        for i in range(parallelism):
            udf = self.udf_class(in_queue=in_queue, worker_id=i, **self.udf_init_kwargs)
            udf.apply_kwargs = kwargs
            self.udfs.append(udf)

        # Start the UDF processes, and then join on their completion
        for udf in self.udfs:
            udf.start()

        for i, udf in enumerate(self.udfs):
            udf.join()

        # Terminate and flush the processes
        for udf in self.udfs:
            udf.terminate()
        self.udfs = []


class UDF(Process):
    def __init__(self, in_queue=None, worker_id=0):
        """
        in_queue: A Queue of input objects to process; primarily for running in parallel
        """
        Process.__init__(self)
        self.daemon = True
        self.in_queue = in_queue
        self.worker_id = worker_id

        # Each UDF starts its own Engine
        # See SQLalchemy, using connection pools with multiprocessing.
        Session = new_sessionmaker()
        self.session = Session()

        # We use a workaround to pass in the apply kwargs
        self.apply_kwargs = {}

    def run(self):
        """
        This method is called when the UDF is run as a Process in a
        multiprocess setting The basic routine is: get from JoinableQueue,
        apply, put / add outputs, loop
        """
        while True:
            try:
                x = self.in_queue.get(True, QUEUE_TIMEOUT)
                self.session.add_all(y for y in self.apply(x, **self.apply_kwargs))
                self.in_queue.task_done()
            except Empty:
                break
        self.session.commit()
        self.session.close()

    def apply(self, x, **kwargs):
        """This function takes in an object, and returns a generator / set / list"""
        raise NotImplementedError()
