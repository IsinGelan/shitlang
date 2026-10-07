
:- use_module(library(lists)).

% :- dynamic do_tracking/0.
% :- assertz(do_tracking).
% no_track :- retractall(do_tracking).
% track :- assertz(do_tracking).

:- dynamic hypothesis/1.
:- dynamic executable/1.

start_tracking :-
    nb_setval(used_facts, []),
    assertz(do_tracking).

record_fact(Fact) :-
    % do_tracking(),
    nb_getval(used_facts, Facts0),
    (   memberchk(Fact, Facts0)
    ->  Facts = Facts0
    ;   Facts = [Fact|Facts0]
    ),
    nb_setval(used_facts, Facts).
record_hypo_fact(Fact, Hypothesis) :-
    record_fact(hypo_fact(Fact, Hypothesis)).

used_facts(Facts) :-
    nb_getval(used_facts, Facts).
print_used_facts :-
    used_facts(Facts),
    forall(member(Fact, Facts), writeln(Fact)).

% ================================
tracked(Fact) :-
    call(Fact),
    (
        hypothesis(H)
        ->  record_hypo_fact(Fact, H)
        ;   record_fact(Fact)
    ).
tracked_name(Name) :-
    atom(Name),
    record_fact(atom(Name)).
tracked_executable(Name) :-
    assertz(executable(Name)),
    record_fact(executable(Name)).

% ================================
% :- table raw_exec/0.
% exec(...) :-
%     raw_exec(...),
%     (hypothesis(H) -> true; tracked_executable(exec(...)))

set_hypothesis(Hypothesis) :-
    retractall(hypothesis(_)),
    assertz(hypothesis(Hypothesis)).

run_hypo(Hypothesis, Goal) :-
    set_hypothesis(Hypothesis),
    (
        call(Goal)
    ->  retractall(hypothesis(Goal)), true
    ;   retractall(hypothesis(Goal)), false
    ).

% ================================
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