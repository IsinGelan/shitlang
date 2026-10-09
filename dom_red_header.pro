:- use_module(library(lists)).

% ================================
% TRACKING FACS, OBJECTS, AND EXECUTABLES
:- dynamic executable/1.

start_tracking :-
    nb_setval(used_facts, []),
    assertz(do_tracking).

record_fact(Fact) :-
    nb_getval(used_facts, Facts0),
    (   memberchk(Fact, Facts0)
    ->  Facts = Facts0
    ;   Facts = [Fact|Facts0]
    ),
    nb_setval(used_facts, Facts).

used_facts(Facts) :-
    nb_getval(used_facts, Facts).

print_used_facts :-
    used_facts(Facts),
    forall(member(Fact, Facts), writeln(Fact)).

tracked(Fact) :-
    call(Fact),
    record_fact(Fact).

tracked_name(Name) :-
    atom(Name),
    record_fact(atom(Name)).

tracked_executable(Name) :-
    assertz(executable(Name)),
    record_fact(executable(Name)).

% ================================
% MEMOIZATION DIRECTIVES
:- dynamic memoized_predicate/1.

% Register predicates declared with :- memoize(Name/Arity).
term_expansion((:- memoize(PI)), []) :-
    nonvar(PI),
    PI = Name/Arity,
    atom(Name),
    integer(Arity),
    Arity >= 0,
    !,
    (   memoized_predicate(PI)
    ->  true
    ;   assertz(memoized_predicate(PI))
    ).

% Check whether a goal's predicate is registered.
should_memoize(Goal) :-
    callable(Goal),
    functor(Goal, Name, Arity),
    memoized_predicate(Name/Arity).

% ================================
% RUNNING GOALS WITH MEMOIZATION
% Memoized result for goals
:- dynamic memo_cache/2.
% Imitating a call stack
:- dynamic evaluating/1.

run(Goal) :-
    (
        should_memoize(Goal)
        -> run_memo(Goal)
        ;  call(Goal)
    ).

run_memo(Goal) :-
    (   memo_cache(Goal, Result)
    ->  Result == true
    ;   evaluating(Goal)
    ->  fail % Prevent infinite recursion (don't call the same goal while evaluating it)
    ;   setup_call_cleanup(
            assertz(evaluating(Goal)),
            (   once(Goal)
            ->  assertz(memo_cache(Goal, true))
            ;   assertz(memo_cache(Goal, false)),
                fail
            ),
            retractall(evaluating(Goal))
        )
    ).

run_all(Goal, AnyTrue) :-
    gensym(run_all_, Key),
    nb_setval(Key, false),
    (
        call(Goal),
        nb_setval(Key, true),
        fail
    ;
        nb_getval(Key, AnyTrue)
    ).