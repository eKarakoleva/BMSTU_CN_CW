"""Module that provides stoppable threads."""

import threading

class Stop(Exception):
    """Exception that signals to a StopThread, that it should stop."""
    pass

class StopThread(threading.Thread):
    """A stoppable thread class."""
    
    def __init__(self, *args, **kwargs):
        """Additional keyword arguments:
            - atom_target is a function, which should be regulary.
    
            This function can raise the Stop Exception, if work is done
            and it should not be run again (that is the thread should
            be stopped).
    
        Also see threading.Thread documentation.
        """
        self.__running = True
        self.__atom_target = kwargs.pop('atom_target', None)
        self.__kwargs = kwargs.get('kwargs', {})
        self.__args = kwargs.get('args', ())
        
        threading.Thread.__init__(self, *args, **kwargs)
    
    def run(self):
        """Method representing the StopThread's activity.

        You may override this method in a subclass and check
        for self.stopped() regulary to keep track, if the thread
        should stop running.
        
        By default, run will run atom_target(*args, **kwargs), if
        atom_target was given as a keyword argument. Otherwhise
        it will fall back to threading.Thread.run()
                
        Also see threading.Thread.run()
        """
        
        # derived from the library code (threading.py)
        try:
            if self.__atom_target:
                while self.__running:
                    self.__atom_target(*self.__args, **self.__kwargs)
            
            # run standard library code, if this thread doesn't
            # have an atom_target
            else:
                threading.Thread.run(self)
        except Stop:
            self.__running = False
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self.__atom_target, self.__args, self.__kwargs
    
    def stop(self):
        """_Signals_ the thread to stop at the next possible step.
        
        There is _no_guarantee_, that the thread will in fact stop,
        and joining the thread could still block indefinitly.
        """
        self.__running = False

    def stopped(self):
        """Checks, if this thread was (or should be) stopped."""
        return not self.__running
