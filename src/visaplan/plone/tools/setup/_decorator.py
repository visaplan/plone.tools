# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Decorators for upgrade steps

Common functionality of the decorators provided by this module:

- They expect the decorated function to accept a context and a logger argument.
  The logger argument might be omitted depending on the usage, so it is
  complemented by the decorator for this cases;
  thus, the decorated function doesn't need any code to handle a missing logger option.

- They use the given or created logger to log the time it took to run the function.

- They catch the KeyboardInterrupt to allow the function to be aborted but not
  abort the foreground Zope process (which will receive a special StepAborted
  exception in this case);
  all other exceptions are logged (including the time the function ran up to
  this point) and re-raised.
"""

# Python compatibility:
from __future__ import absolute_import

# Standard library:
from functools import wraps
from time import time

# Logging / Debugging:
import logging

__all__ = [
        # decorators:
        'step',
        # noch unfertig: 
        # 'upgrade_step',
        'make_step_decorator',
        # exceptions:
        'StepAborted',
        ]


class StepAborted(Exception):
    """
    Vom Dekorator @step geworfen, wenn in einem Migrationsschritt eine
    KeyBoard-Exception ausgelöst wurde
    """


def step(func):
    """
    Dekorator für Migrationsschritte:
    - ergänzt ggf. fehlendes logger-Argument
    - stoppt die Zeit
    - (experimentell:)
      erlaubt das Weiterlaufen der Zope-Instanz auch nach manuellem Abbruch
      des Migrationsschritts
    """
    # da die def-Anweisung hier nicht ausgeführt wird, ist eine implizite
    # "Impfung" der verpackten Funktion mit zusätzlichen Variablen (wie z.B.
    # "site") leider nicht möglich; dafür würden zustäzliche Argumente
    # benötigt, und mithin eine Änderung der Signatur.

    @wraps(func)
    def wrapper(context, logger=None):
        funcname = func.__name__
        if logger is None:
            logger = logging.getLogger('setup:'+funcname)
        _started = time()
        try:
            res = func(context, logger)
        except Exception as e:
            delta = time() - _started
            if isinstance(e, KeyboardInterrupt):
                logger.error('%(funcname)s aborted after %(delta)5.2f seconds',
                             locals())
                logger.exception(e)
                raise StepAborted
            else:
                logger.error('%(funcname)s: %(e)r after %(delta)5.2f seconds',
                             locals())
                logger.exception(e)
                raise
        else:
            delta = time() - _started
            logger.info('%(res)r <-- %(funcname)s (%(delta)5.2f seconds)', locals())
        return res

    return wrapper


def upgrade_step(destination, **kwargs):
    """
    Gib einen Dekorator zur einmaligen Verwendung zurück.
    Es wird als erstes Argument die Zielversion (destination)
    angegeben; weitere werden üblicherweise in einem Dict gesammelt:

    >>> deco_kwargs = {'package': __package__, 'module': __name__}
    >>> @upgrade_step(1001, **deco_kwargs)
    ... def create_interesting_folder(context, logger):
    ...     pass

    Der Dekorator sorgt für das (je nach Aufruf fehlende) logger-Argument;
    protokolliert wird:
    - die Zielversion (destination)
    - der Name der Funktion
    - jeweils wenn übergeben:
      - der Name des Python-Packages (package)
      - der Name des Moduls (module)
      - die Revisionsnummer (rev), normalerweise als String

    Die Logik ist wie folgt:
    - upgrade_step wird aufgerufen und verarbeitet die übergebenen Argumente,
      um eine Funktion mit einem Argument <func> zu erzeugen,
      die die übergebene Funktion dekoriert
    - die so generierte Funktion bekommt die letztlich zu dekorierende Funktion
      übergeben und gibt eine Wrapper-Funktion zurück, die folgendes tut:
      - sie erzeugt einen Logger, falls nicht übergeben,
        und ergänzt so das an die dekorierte Funktion übergebene logger-Argument;
      - sie protokolliert das Paket (sofern package übergeben; dringend
        empfohlen!) und die Zielversion
      - sie protokolliert den Namen der dekorierten Funktion
      - sie ruft die dekorierte Funktion auf und merkt sich den Zeitpunkt
      - sie protokolliert den Rückgabewert und die Brutto-Laufzeit der
        dekorierten Funktion
        - im Fehlerfall werden entsprechende Informationen protokolliert
      - schließlich nochmals ein Protokolleintrag für das Paket und die
        Zielversion
    """

    def make_wrapper():
        """
        package = package
        destination = destination
        rev = rev
        """
        rev = kwargs.pop('rev', 0)
        package = kwargs.pop('package')
        module = kwargs.pop('module', None)
        logger = kwargs.pop('logger', None)
        logger_name = kwargs.pop('logger_name', 'setup:%(funcname)s')

        @wraps(func)
        def wrapper(context, logger=logger):
            funcname = func.__name__
            package = package
            destination = destination
            rev = rev
            if logger is None:
                logger = logging.getLogger(logger_name % locals())
            logger.info('[ updating %(package)s to version %(destination)s ... [',
                        locals())
            '''            
                        {'package': package,
                         'destination': destination,
                        })
            '''            
            _started = time()
            if rev:
                logger.info('%(funcname)s@%(rev)s started', locals())
            else:
                logger.info('%(funcname)s started', locals())
            try:
                res = func(context, logger)
            except Exception as e:
                delta = time() - _started
                if isinstance(e, KeyboardInterrupt):
                    logger.error('%(funcname)s aborted after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    logger.error('] ... update of %(package)s to version'
                                 ' %(destination)s aborted ]',
                                 locals())
                    raise StepAborted
                else:
                    logger.error('%(funcname)s: %(e)r after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    logger.error('] ... update of %(package)s to version'
                                 ' %(destination)s failed ]',
                                 locals())
                    raise
            else:
                delta = time() - _started
                logger.info('%(funcname)s completed (%(delta)5.2f seconds)', locals())
                logger.info('] ... %(package)s updated to version %(destination)s ]',
                            locals())
            return res

        return wrapper
    return make_wrapper()


def make_step_decorator(**kwargs):
    """
    Erzeuge einen Dekorator wie vorstehende Funktion --> step,
    aber ergänze bei der Protokollierung des Aufrufs, gemäß benannten
    Argumenten:
    - rev --> die svn-Revision des aufrufenden Moduls;
      z. B., wenn das svn:keyword "Revision" aktiv ist:
      >>> MODULE_REVISION = '$Revision: 31126 $'[8+3:-2]
    """
    rev = kwargs.pop('rev', 0)
    mask = 'setup:%(funcname)s'
    if rev:
        int(rev)
        mask += '@' + rev

    def make_wrapper(func, rev=rev):
        @wraps(func)
        def wrapper(context, logger=None):
            funcname = func.__name__
            rev = rev
            if logger is None:
                logger = logging.getLogger('setup:'+funcname)
            _started = time()
            if rev:
                logger.info('%(funcname)s@%(rev)s started', locals())
            try:
                res = func(context, logger)
            except Exception as e:
                delta = time() - _started
                if isinstance(e, KeyboardInterrupt):
                    logger.error('%(funcname)s aborted after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    raise StepAborted
                else:
                    logger.error('%(funcname)s: %(e)r after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    raise
            else:
                delta = time() - _started
                logger.info('%(funcname)s completed (%(delta)5.2f seconds)', locals())
            return res

        return wrapper
    return make_wrapper
