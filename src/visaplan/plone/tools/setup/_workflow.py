# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _workflow
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types

# Standard library:
from collections import defaultdict

# Zope:
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException

# visaplan:
from visaplan.tools.classes import DictOfSets

# Local imports:
from visaplan.plone.tools.setup._roles import set_local_roles
from visaplan.plone.tools.setup._watch import make_watcher_function

# Logging / Debugging:
import logging
from pdb import set_trace

# Exceptions:


__all__ = [
        'make_transition_applicator',
        ]


TRANSITIONS_MAP = {}
for from_state, to_state, tr in (
    ('restricted', 'visible',    'make_visible'),
    ('restricted', 'published',  'make_public'),
    ('visible',    'published',  'make_public'),
    ('visible',    'restricted', 'make_restricted_again'),
    ('published',  'visible',    'make_visible_again'),
    ('published',  'restricted', 'make_restricted_again'),
    # für Vortragsseiten, die in Demo-Kursen benötigt werden:
    ('inherit',    'visible',    'make_visible'),
    ('inherit',    'published',  'make_public'),
    # nichts zu tun, aber kein Fehler:
    ('restricted', 'restricted', None),
    ('visible',    'visible',    None),
    ('published',  'published',  None),
    ):
    TRANSITIONS_MAP[(from_state, to_state)] = tr
def make_transition_applicator(**kwargs):  # ---- [ m._t._a. ... [ -[[
    """
    Erzeuge eine Funktion, die den Workflow-Status eines als brain übergebenes
    Objekts ändert; dabei kann der Zielstatus aus der UID ermittelt werden
    (siehe uids_tuples).

    Argumente:
    - {default_,}target_state - der Zielstatus, wenn nicht aus uids_tuples zu
                                ermitteln
    - uids_tuples - eine Liste von (set, status, funktion)-Tupeln:
                    set - ein Set von UIDs, die den <status> (oder "besser")
                          erhalten sollen;
                    funktion - eine für die Objekte mit dem Zielstatus <status>
                               aufzurufende Funktion (z. B. zur rekursiven
                               Ermittlung der UIDs der verwendeten Objekte)
    - transitions_map - siehe TRANSITIONS_MAP
    - returns - was soll die Funktion zurückgeben?
      'changed' - True, wenn geändert wurde, sonst False (Vorgabewert)
      'target' - True, wenn der Zielstatus der gewünschte ist, sonst False
      'both' - ein 2-Tupel (changed, target)
      'error' - wie 'changed', aber mit Exception z. B. bei unbekannten
                Transitionen
    - doit_function - eine Funktion, die (nach den sonstigen Prüfungen)
                      entscheidet, ob die Transition (jetzt) angewendet werden
                      soll; sollte im anderen Fall eine Datenstruktur füllen,
                      um die (verzögerten) Transitionen später nachzuholen.
                      Signatur: f(brain, target_state)
    - set_inherit - soll die Akquisition von Zugriffsrechten vom Elternobjekt
                    umgeschaltet werden?  Mögliche Werte:
                    True - einschalten
                    False - ausschalten
                    'auto' - einschalten für Zielstatus 'inherit' oder
                             'published', sonst ausschalten
                    'autorestrict' - wie 'auto',
                                     aber nichts tun für 'published' (Vorgabe)
                    None - nichts tun
                    Die etwaige Umschaltung wird ungeachtet des Ergebnisses
                    einer <doit_function> ausgeführt, nicht aber wenn die
                    Transition lt. der internen <done_sets> (Schlüssel:
                    Zielstatus) schon durchgeführt wurde.
    - localroles_function - insbesondere wichtig für den Zielstatus
                    'restricted': eine Funktion, die bestimmt,
                    - welche "Prinzipale" (hier i.d.R.: Gruppen)
                    - welche lokalen Rollen
                    - zugewiesen (Vorgabe) oder entzogen bekommen sollen;
                    Signatur: f(brain, target_state).
                    Als Rückgabewert wird eine Liste von (id, [Rolle,...],
                    add)-Tupeln erwartet;
                    siehe --> make_simple_localroles_function
    - set_best_status - soll für das jeweilige Objekt der "beste" Status
                        gesetzt, d.h. ein etwaiger done-Vermerk für einen
                        nachgeordneten Status ignoriert werden?
                        (Siehe DictOfSets und die durch <uids_tuples>
                        vorgegebene Reihenfolge)
                        Vorgabe: True, wenn <uids_tuples> übergeben und nicht
                        leer, ansonsten False
    - force - soll eine Transition durchgeführt werden, obwohl sie für das
              übergebene Katalogobjekt (Kriterium: UID) oder einen "besseren"
              (=öffentlicheren) Zielstatus bereits durchgeführt wurde?
              (verwendet internes Dict <done_sets>)
    - regard_current - soll eine Transition als erfolgreich betrachtet werden
                       (insbesondere incl. der <done_sets>), wenn (ungeachtet
                       etwaiger Fehler) das Ergebnis stimmt?
    - shortcircuit - Transition von vornherein nicht versuchen, wenn der
                     Zielstatus schon vorliegt. Kann viel Zeit sparen,
                     insbesondere bei Medien mit Vorschaubildern!

    Debugging-Optionen:

    - watched_uid_and_status - siehe --> make_watcher_function;
                     set_trace, wenn apply_transition sich anschickt, das
                     Objekt mit der UID <uid> auf <status> zu setzen
    - tell_about_uids - ein Dict, {<uid>: <label>, ...},
                        oder eine Liste [(<uid>, <label>), ...];
                     wenn angegeben, wird zusätzlich eine Funktion
                     zurückgegeben, die über die Größen der internen Sets
                     informiert und darüber, ob die hier angegebenen UIDs
                     jeweils darin enthalten sind.
                 ACHTUNG:
                     Der Rückgabewert ist dann also keine einzelne Funktion,
                     sondern ein 2-Tupel (<apply_transition>, <tell...>)!
    """
    # ]]------ [ make_transition_applicator: Argumente ... [
    status_set = defaultdict(set)
    target_sets = DictOfSets()
    status_func = {}
    # Behandlung schon erledigter ...
    done_sets = DictOfSets()
    force = kwargs.pop('force', False)
    shortcircuit = kwargs.pop('shortcircuit', True)

    regard_current = kwargs.pop('regard_current', True)
    if 'default_target_state' in kwargs:
        default_target_state = kwargs.pop('default_target_state')
    else:
        default_target_state = kwargs.pop('target_state', None)
    uids_tuples = kwargs.pop('uids_tuples')
    for tup in uids_tuples:
        theset, target_state, func = tup
        if target_state in done_sets:
            raise ValueError('duplicate status %(target_state)r!' % locals())
        elif not isinstance(target_state, six_string_types):
            raise ValueError('Workflow status expected! (%target_state()r)'
                             % locals())
        target_sets.add_set(target_state)
        done_sets.add_set(target_state)
        if theset is None:
            if default_target_state is None:
                raise ValueError('No set for %(target_state)r,'
                                 ' and no default_target_state!'
                                 % locals())
            elif target_state != default_target_state:
                raise ValueError('No set for %(target_state)r which doesn\'t match'
                                 ' default_target_state %(default_target_state)r!'
                                 % locals())
            else:
                theset = set()
        elif not isinstance(theset, set):
            theset = set(theset)
        status_set[target_state] = theset
        target_sets[target_state].update(theset)
        status_func[target_state] = func
    set_best_status = kwargs.pop('set_best_status', bool(uids_tuples))
    del uids_tuples
    # neue UIDs den target_sets nur hinzufügen, wenn der Zielstatus
    # in den ursprünglich angegebenen enthalten ist:
    target_values = target_sets.ordered_keys()
    transitions_map = kwargs.pop('transitions_map', TRANSITIONS_MAP)
    returns = kwargs.pop('returns', 'changed')
    r_pool = 'changed target both error'.split()
    if returns not in r_pool:
        raise ValueError('invalid "returns" value (%(returns)r); '
                         'one of %(r_pool)s expected'
                         % locals())
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('apply_transition')

    verbosity = kwargs.pop('verbosity', 1)

    doit_function = kwargs.pop('doit_function', None)
    if doit_function is not None:
        doit = None
    else:
        doit = kwargs.pop('doit', True)
        if doit not in (False, True):
            raise ValueError('invalid "doit" value (%(doit)r)'
                             % locals())

    # ---------------------- [ Lokale Rollen ... [
    set_inherit = kwargs.pop('set_inherit', 'autorestrict')
    if set_inherit is None:
        pass
    elif set_inherit not in (False, True, 'auto', 'autorestrict'):
        raise ValueError('invalid "set_inherit" value (%(set_inherit)r)'
                         % locals())
    localroles_function = kwargs.pop('localroles_function', None)
    # ---------------------- ] ... Lokale Rollen ]

    # ---------- [ für Debugging (set_trace) ... [
    if 'watched_uid_and_status' in kwargs:
        tup = kwargs.pop('watched_uid_and_status')
        if tup:
            watched_case = make_watcher_function(tup,
                                                 logger=logger,
                                                 msg='WATCHED CASE: uid = %(key)r'
                                                 ' --> status = %(val)r!')
            logger.warn('DEBUGGING: set_trace, wenn ein beobachteter Fall '
                        'eintritt!')
        else:
            watched_case = gimme_False
    else:
        watched_case = gimme_False
    # ---------- ] ... für Debugging (set_trace) ]
    # -------- ] ... make_transition_applicator: Argumente ]

    tell_about_uids = kwargs.pop('tell_about_uids', False)
    if tell_about_uids:
        if isinstance(tell_about_uids, dict):
            tell_about_uids = list(tell_about_uids.items())

    # ------------ [ m._t._a.: generierte Infofunktion ... [
    stored_hits = {'prev': None,
                   'current': [],
                   }
    def summary(label=''):
        """
        Gib eine Zusammenfassung aus;
        lies hierzu folgende Variablen aus der Closure:

        done_sets -- die Sets mit den Erledigungen
        target_sets -- die Sets mit den gefundenen (oder explizit angegebenen)
                       UIDs
        stored_hits -- ...
        """
        info = []
        if label:
            label = label.strip()
        elif label is None:
            label = ''
        if label:
            label = label.join((' (', ')'))

        current_hits = stored_hits['current']
        has_hits = False
        found_targets = False
        for title, dos in [   # DictOfSets
            ('Zielstatus-Sets', target_sets),
            ('DONE-Sets',       done_sets),
            ]:
            if len(dos):
                info.append(title)
                for status in dos.ordered_keys():
                    theset = dos[status]
                    contains = []
                    for key, txt in tell_about_uids:
                        if key in theset:
                            current_hits.append((key, status, 'done'))
                            if key != txt:
                                contains.append('%(txt)s (%(key)s)' % locals())
                            else:
                                contains.append(key)
                    L = len(theset)
                    line = '%(L)7d %(status)r' % locals()
                    if contains:
                        has_hits = True
                        line += '; contains '+ ', '.join(contains)
                    info.append(line)
        if info:
            info.insert(0, '')
            info.append('')
        else:
            info.append('<empty!>')
        logger.info('apply_transition: SUMMARY%s {{%s}}',
                    label,
                    '\n  '.join(info))
        prev_hits = stored_hits['prev']
        if prev_hits is None:
            res = has_hits
        else:
            res = current_hits != prev_hits
        stored_hits['prev'] = current_hits
        stored_hits['current'] = []
        return res
    # ------------ ] ... m._t._a.: generierte Infofunktion ]

    # --------- [ m._t._a.: generierte Arbeitsfunktion ... [
    def apply_transition(brain, target_state=None,
                         default_target_state=default_target_state,
                         doit=doit,
                         logger=logger,
                         verbosity=verbosity,
                         force=force,
                         regard_current=regard_current,
                         set_inherit=set_inherit,
                         set_best_status=set_best_status,
                         localroles_function=localroles_function,
                         shortcircuit=shortcircuit):
        """
        Wende eine Workflow-Transition an und gib einen oder mehrere
        Wahrheitswerte zurück (--> erzeugende Funktion, <returns>)

        brain - das jeweilige Objekt wird als Katalogobjekt erwartet!
        target_state - wenn None, werden zunächst die Sets aus der erzeugenden
                       Funktion durchsucht (--> uid_tuples)
        default_target_state - verwendet, wenn <target_state> nach etwaiger
                       Suche in den <uid_tuples> immer noch None
        doit - wenn None, wird die <doit_function> (siehe erzeugende Funktion)
               verwendet, um zu entscheiden, ob die Transition direkt
               durchgeführt werden soll, oder andernfalls das Objekt für die
               spätere Verarbeitung vorzumerken
        logger - der zu verwendende Logger (Vorgabe aus erzeugender Funktion)
        verbosity - Ausführlichkeit, dto.
        force - <done_sets> ignorieren (siehe erzeugende Funktion)
        regard_current - wenn der aktuelle schon dem Zielstatus entspricht,
                         dies auch im Fehlerfall als erfolgreich behandeln;
                         weitgehend obsolet durch --> shortcircuit
        set_inherit - ein Wahrheitswert oder 'auto{,restrict}', oder None.
                      Siehe oben.
                      Wenn None, wird die etwaige Akquisition lokaler Rollen
                      nicht modifiziert.
        set_best_status - Vorgabewert siehe oben
        shortcircuit - wenn der aktuelle schon dem Zielstatus entspricht,
                       die Aktion als erfolgreich durchgeführt betrachten
                       (wenn auch ohne Änderungen)
        """
        # TODO: add_viewers_group, für restricted:
        # - auch, wenn Status schon 'restricted' ist (Reparatur)
        # - abhängig z. B. von portal_type; also z. B. durch Funktion zu regeln
        current_state = brain.review_state
        changed = False
        target_ok = True
        done = False
        o = None
        uid = brain.UID
        if target_state is None:
            target_state = target_sets.first_hit(uid, default_target_state)
            if target_state is None:
                target_state = default_target_state
                if watched_case(uid, target_state):
                    set_trace()
            if target_state is None:
                logger.error('Unknown target_state for UID %(uid)r', locals())
                if returns == 'error':
                    raise ValueError('Unknown target_state for UID %(uid)r'
                                     % locals())
                else:
                    changed, target_ok = None, None
                    done = True
        else:
            if watched_case(uid, target_state):
                set_trace()
            if target_state in target_values:
                # Zielstatus wurde übergeben; dem korrekten Set hinzufügen:
                target_sets[target_state].add(uid)

        # ----------------------- [ Zielstatus bekannt ... [
        if (not done   # der Regelfall!
                       # der Zielstatus wurde übergeben,
                       # konnte aus einem der Sets ermittelt werden,
                       # oder es gab zumindest einen Vorgabewert:
            and target_state is not None
            ):
            o = brain.getObject()
            # Es werden die Statuus geordnet überprüft;
            # was schon auf 'published' gesetzt wurde, braucht für 'published',
            # 'visible' und etwaige weitere nicht mehr berücksichtigt zu
            # werden.
            if set_best_status:
                done_state = done_sets.first_hit(uid, target_state)
            else:
                done_state = done_sets.first_hit(uid)
            if done_state is not None:
                logger.info('UID %(uid)r (--> %(target_state)r)'
                            ' found as done for %(done_state)r',
                            locals())
                if not force:
                    done = True  # set_inherit ist davon unabhängig

            # ---- [ nicht erledigt lt. done-Sets ... [
            if not done:
                func = status_func.get(target_state, None)
                if func is not None:
                    func(brain)  # z. B. rekursive Ermittlung der UIDs!
                if doit is None:
                    doit = doit_function(brain, target_state) or False
                if doit and shortcircuit:
                    if current_state == target_state:
                        changed, target_ok = False, True
                        done_sets.add(uid, target_state)
                        doit = False
                        pt = brain.portal_type
                        logger.info('%(uid)r %(pt)r (%(current_state)r): '
                                    'Keine Aktion erforderlich',
                                    locals())
                transition = None
                if doit:
                    # nun die Transition ermitteln:
                    try:
                        transition = TRANSITIONS_MAP[(current_state, target_state)]
                    except KeyError:
                        if regard_current and (current_state == target_state):
                            logger.info('%(o)r: keine Transition %(current_state)r --> %(target_state)r,'
                                        'aber der Zielstatus stimmt schon',
                                         locals())
                            changed, target_ok = None, True
                            done_sets.add(uid, target_state)
                        else:
                            logger.error('%(o)r: keine Transition %(current_state)r --> %(target_state)r bekannt!',
                                         locals())
                            if returns == 'error':
                                raise
                            else:
                                changed, target_ok = None, current_state == target_state
            # ---- ] ... nicht erledigt lt. done-Sets ]
            if not done and transition is None:
                if verbosity >= 3:
                    logger.info('Objekt %(uid)r bleibt %(current_state)r', locals())
                changed, target_ok = False, current_state == target_state
                done = True
            # --------- [ <transition> ist nun gesetzt ... [
            if not done:  # transition hat jetzt einen verwendbaren Wert
                # --------------- [ WF-Transition ... [
                if doit is None:
                    doit = doit_function(brain, target_state)
                if doit:
                    if o is None:
                        o = brain.getObject()
                    if verbosity >= 2 or brain.portal_type == 'Folder':
                        logger.info('%(uid)r %(o)r (%(current_state)r):'
                                    ' %(transition)s) ...',
                                    locals())
                    wft = getToolByName(o, 'portal_workflow')
                    try:
                        res = wft.doActionFor(o, transition)
                    except WorkflowException as e:
                        if regard_current and (current_state == target_state):
                            logger.info('%(uid)r, Transition fehlgeschlagen,'
                                        'aber der Zielstatus %(target_state)r stimmt schon (%(o)r)',
                                         locals())
                            target_ok = True
                            done_sets.add(uid, target_state)
                        else:
                            logger.error('%(uid)r %(o)r, Transition %(transition)r: %(e)r',
                                         locals())
                            target_ok = False
                    else:
                        done_sets.add(uid, target_state)
                        if verbosity >= 1:
                            logger.info('%(uid)r %(o)r, %(transition)s: OK', locals())
                        changed, target_ok = True, True
                else:
                    o = None
                    changed, target_ok = None, False
                # --------------- ] ... WF-Transition ]
            # --- [ Berechtigungs-Akquisition ... [
            if set_inherit is not None:
                if set_inherit == 'auto':
                    set_inherit = target_state in ('published', 'inherit')
                elif set_inherit == 'autorestrict':
                    if target_state in ('published',):
                        set_inherit = None
                    elif target_state == 'inherit':
                        set_inherit = True
                    else:
                        set_inherit = False
                if set_inherit is not None:
                    if o is None:
                        o = brain.getObject()
                    sharing = o.restrictedTraverse('@@sharing')
                    act_ = set_inherit and 'activate' or 'deactivate'
                    logger.info('%(uid)r %(o)r (-> %(target_state)r): '
                                '%(act_)s permission inheritance ...',
                                locals())
                    if sharing.update_inherit(set_inherit):
                        changed = True
                        logger.info('%(uid)r %(o)r (-> %(target_state)r): '
                                    'permission inheritance %(act_)sd',
                                    locals())
                    elif verbosity >= 1:
                        logger.info('%(uid)r %(o)r (-> %(target_state)r): '
                                    'permission inheritance not changed',
                                    locals())
            # --- ] ... Berechtigungs-Akquisition ]
            if localroles_function is not None:
                if set_local_roles(brain=brain, o=o,
                                   func=localroles_function,
                                   target_state=target_state,
                                   logger=logger):
                    changed = True
            # ---- ] ... <transition> ist nun gesetzt ]
        # ----------------------- ] ... Zielstatus bekannt ]

        if returns == 'target':
            return target_ok
        elif returns == 'both':
            return changed, target_ok
        else:  # 'changed' oder 'error'
            return changed
    # --------- ] ... m._t._a.: generierte Arbeitsfunktion ]

    if tell_about_uids:
        return apply_transition, summary
    return apply_transition
    # ----------------------------- ] ... make_transition_applicator ]


