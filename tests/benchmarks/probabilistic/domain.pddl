(define (domain coin)
  (:requirements :strips)
  (:predicates (ready) (heads) (tails))
  (:action flip
    :precondition (ready)
    :effect (and (whenp 0.5 (heads))
                 (whenp 0.5 (tails)))))
