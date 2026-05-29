(define (domain bomb-toilet)
  (:requirements :strips)
  (:predicates (bomb-in-package ?p) (toilet-clogged) (defused))
  (:action dunk-package
    :parameters (?p)
    :precondition (not (toilet-clogged))
    :effect (and (when (bomb-in-package ?p) (defused))
                 (toilet-clogged)))
  (:action flush
    :precondition (toilet-clogged)
    :effect (not (toilet-clogged))))
