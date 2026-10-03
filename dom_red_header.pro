
:- use_module(library(lists)).

:- dynamic do_tracking/0.
no_track :- retract(do_tracking()).
track :- assertz(do_tracking()).
do_tracking.

:- dynamic executable/1.

start_tracking :-
    nb_setval(used_facts, []),
    assertz(do_tracking).

record_fact(Fact) :-
    do_tracking,
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

untracked(Call) :-
    no_track,
    call(Call),
    track.

% ================================
% this doesn't work cause run_all_any_true is not local,
% so it will not work if subcalls of Goal also call run_all/2
run_all(Goal, AnyTrue) :-
    nb_setval(run_all_any_true, false),
    (   call(Goal),
        nb_setval(run_all_any_true, true),
        fail
    ;   nb_getval(run_all_any_true, AnyTrue)
    ).

call_rule(Goal, true) :-
    call(Goal),
    !.
call_rule(_, false).