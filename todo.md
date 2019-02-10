* add progress bar which is context aware (notebook, command line)
* add altair based analysis to scenario discovery
* add logistic regression scenario discovery approach
* review parallelization code, too much unnecessary copying seems
  to be going on at the moment
* add documentation on how to develop connectors
* ENUMS for density styles, samplers
* operator probabilities as additional convergence metrics in case of 
  generational BORG
* add feature scoring over time, and sobol over time
* Sobol style confidence intervals around prim thresholds, is basically a small
  extension to the resampling statistic. 
* parametrization of feature scoring according to Marc's paper.
* add gini obj to PRIM --> adds classification as possible type of prim run