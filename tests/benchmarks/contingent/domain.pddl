(define (domain medicine)
  (:requirements :strips :adl)
  (:predicates (sick) (cured))
  (:action diagnose
    :precondition (and)
    :observe (sick))
  (:action treat
    :precondition (sick)
    :effect (and (cured) (not (sick))))
  (:action skip-treatment
    :precondition (not (sick))
    :effect (cured)))
