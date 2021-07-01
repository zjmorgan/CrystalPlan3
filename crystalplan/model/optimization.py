""" Optimization of various parameters
"""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id: goniometer.py 1174 2010-04-23 14:58:40Z 8oz $

#--- General Imports ---
import numpy as np
import random
import copy

#--- Model Imports ----
from crystalplan.model import instrument
from crystalplan.model import experiment
from crystalplan.model import goniometer

from crystalplan.pyevolve import G1DList
from crystalplan.pyevolve import Consts
from crystalplan.pyevolve import GSimpleGA
from crystalplan.pyevolve import GenomeBase
from crystalplan.pyevolve import Selectors
from crystalplan.pyevolve import Crossovers
from crystalplan.pyevolve import Statistics
from crystalplan.pyevolve import DBAdapters
from crystalplan.pyevolve import Initializators

import crystalplan.pyevolve


#--- Traits Imports ---
from traits.api import HasTraits,Int,Float,Str,Property,Bool, List
from traitsui.api import View,Item,Label,Heading, Spring, Handler, Group
from traitsui.menu import OKButton, CancelButton
from crystalplan.model.instrument import PositionCoverage


# ===========================================================================================
# ===========================================================================================
class OptimizationParameters(HasTraits):
    optimization_running = Bool(False)

    number_of_orientations = Int(10, desc="the number of orientations you want in the sample plan.")
    fixed_orientations = Bool(label="Add Fixed Orientations?", desc="to keep the list of sample orientations currently in the Experiment Plan as fixed orientations. \nThe number of orientations calculated by the optimizer is ADDED to the fixed orientations from the list.")
    desired_coverage = Float(85.0, desc="the percent reciprocal-space coverage you want. The optimization will stop when it reaches this point.")
    use_volume = Bool(False, label='Optimize Q-volume rather than reflections?', desc='That the optimization will be performed using the reciprocal space volume calculation. \nIf unchecked, the coverage will be calculated as the % of individual reflections that were measured.')
    use_symmetry = Bool(False, label='Use crystal symmetry', desc="to consider crystal symmetry in determining reflection/volume coverage. For example, with mmm symmetry, each reflection has 8 equivalent hkl values. A peak is considered measured if any of the hkl were measured.")
    auto_increment = Bool(False, label='Auto increment # of orientations?', desc="that if the optimization does not converge in the # of generations, add one to the # of sample orientations and try again.")
    avoid_edges = Bool(True, desc="to try to keep reflections away from the detector edges. Any reflection measured close to an edge (within the distance specified below, edge_x, or edge_y) is not considered as 'measured'.")
    edge_x_mm = Float(5.0, label="X-edge in mm", desc="how far away from the edges reflections should be (in X, so how far from the vertical edges)")
    edge_y_mm = Float(5.0, label="Y-edge in mm", desc="how far away from the edges reflections should be (in Y, so how far from the horizontal edges)")


    population = Int(10, desc="the number of individuals to evolve.")
    max_generations = Int(10000, desc="the maximum number of generations to evolve before giving up.")
    pre_mutation_rate = Float(0.5, label='Worst-gene mutation rate', desc="that the n-th worst sample orientations will be mutated prior to mating.")
    worst_gene_location_randomizer = Float(0.4, label='Randomizer of worst-gene location', desc='When picking the worst gene to randomize, randomize the selection by this much so that perhaps the 2nd-worst gene gets changed instead.')
    mutation_rate = Float(0.02, desc="the probability of randomized mutation per gene.")
    mutate_by_nudging = Bool(True, desc='that mutations of a gene "nudge" its position over by a random angle. If unchecked, the mutation is that the position is completely randomized.')
    nudge_amount = Float(5.0, label='Nudge amount (%)', desc='the width of the normal distribution of nudging that will be done on the angles, as a percentage of the allowable range.')
    crossover_rate = Float(0.01, desc="the probability of cross-over.")
    use_multiprocessing = Bool(False, desc="to use multiprocessing (multiple processors) to speed up calculation.")
    number_of_processors = Int(10, desc="the number of processors to use, if multiprocessing is enabled. Enter <=0 to use all the processors available. Try to keep your population = a multiple of the # of processors.")
    use_old_population = Bool(False)
    elitism = Bool(True, desc="to use elitism, which means to keep the best individuals from the previous generation.")
    elitism_replacement = Int(1, desc="the Elitism replacement number - how many of the best individuals from the previous generation to keep.")


    view = View(
        Group(
            Item('number_of_orientations', enabled_when="not optimization_running"),
            Item('fixed_orientations', enabled_when="not optimization_running"),
            Item('desired_coverage'),
            Item('use_volume', enabled_when="not optimization_running"),
            Item('use_symmetry', enabled_when="not optimization_running"),
            Item('avoid_edges', enabled_when="not optimization_running", visible_when="not use_volume"),
            Item('edge_x_mm', enabled_when="not optimization_running", visible_when="not use_volume"),
            Item('edge_y_mm', enabled_when="not optimization_running", visible_when="not use_volume"),
            Item('auto_increment'),
            label='Optimization Settings'
        ),
        Group(
            Item('population', enabled_when="not optimization_running"),
            Item('max_generations'),
            Item('pre_mutation_rate', visible_when="not use_volume"),
            Item('worst_gene_location_randomizer', visible_when="not use_volume"),
            Item('mutation_rate'),
            Item('mutate_by_nudging'),
            Item('nudge_amount', enabled_when="mutate_by_nudging"),
            Item('crossover_rate'),
            Item('elitism'),
            Item('elitism_replacement'),
            Item('use_multiprocessing'),
            Item('number_of_processors', enabled_when="use_multiprocessing"),
            label='Genetic Algorithm Settings'
        ),
        Spring(label=' ')
        )



# ===========================================================================================
# ===========================================================================================
class GeneAngles(object):
    """Chromosome objects encodes the data about a single individual in the GA optimization
    algorithm"""
    
    #---------------------------------------------------------------
    def __init__(self, copied_object=None):
        #This will initialize the angles at random
        if copied_object is None:
            self.mutate()
        else:
            #Make a copy of the list of angles
            self.angles = [x for x in copied_object.angles]

    #---------------------------------------------------------------
    def __str__(self):
        instr = instrument.inst
        return "(%s)" % ", ".join([ai.pretty_print(value, True) for (ai, value) in zip(instr.angles, self.angles)])

    #---------------------------------------------------------------
    def __repr__(self):
        return self.__str__()

    #---------------------------------------------------------------
    def mutate(self):
        """Mutate (randomize) the angles."""
        instr = instrument.inst
        #Match the # of angle
        self.angles = []
        #@type ai AngleInfo
        for ai in instr.angles:
            #Pick a random angle and add it
            self.angles.append( ai.get_random() )

    #---------------------------------------------------------------
    def nudge(self, percent):
        """Randomly nudge the position by the provided amount (in % of the allowable range)"""
        if percent <= 0: return
        for i in range(len(self.angles)):
            angle_info = instrument.inst.angles[i] #@type angle_info AngleInfo
            max = angle_info.random_range[1]
            min = angle_info.random_range[0]
            amount = (max - min) * percent / 100.0
            newval = self.angles[i] + np.random.normal(scale=amount)
            if newval > max: newval = max
            if newval < min: newval = min
            self.angles[i] = newval



# ===========================================================================================
class ChromosomeAngles(G1DList.G1DList):
    """Subclass of G1D List fixing the copy and clone() methods."""
    premutator = None
    #---------------------------------------------------------------
    def __init__(self, size):
        #Call the parent initializer
        #print "ChromosomeAngles init"
        G1DList.G1DList.__init__(self, size)
        GenomeBase.GenomeBase.__init__(self)
        self.genomeList = []
        self.listSize = size

    #---------------------------------------------------------------
    def randomize(self):
        """Make a random genome for this chromosome."""
        self.genomeList = [GeneAngles() for x in range(self.listSize)]

    #---------------------------------------------------------------
    def copy(self, g, keep_list_size=False):
        """ Copy genome to 'g'
        Parameters:
            g: genome in which we copy this one.
            keep_list_size: set to True to keep the list size of the 'self' object.
                New elements are added (randomized) if needed.
                Excess elements are trimmed at random if needed.
        """
        #print "ChromosomeAngles.copy() called."
        #Copy a bunch of parameters
        GenomeBase.GenomeBase.copy(self, g)
        #Copy any possible attributes
        attributes = ['unique_measurements', 'coverage']
        for att in attributes:
            if hasattr(self, att):
                setattr(g, att, getattr(self, att))
            
        #Do a copy of each "GeneAngles" object
        g.genomeList = [GeneAngles(x) for x in self.genomeList]

        if keep_list_size and not (g.listSize == self.listSize):
            #Adjust the copied size
            diff = g.listSize - self.listSize
            if diff > 0:
                #Need to add diff random elements
                g.genomeList += [GeneAngles() for x in range(diff)]
            elif diff < 0:
                #Remove -diff elements at random
                while diff < 0:
                    g.genomeList.pop( random.randint(0, len(g.genomeList)-1) )
                    diff += 1
        else:
            #Do an exact copy
            g.listSize = self.listSize

    #---------------------------------------------------------------
    def clone(self):
        """ Return a new instace copy of the genome
        :rtype: the G1DList clone instance"""
        newcopy = ChromosomeAngles(self.listSize)
        self.copy(newcopy)
        return newcopy


# ===========================================================================================
def ChromosomeInitializatorRandom(genome, **args):
    """ Randomized Initializator for the Chromosome
    """
    #   print "ChromosomeInitializatorRandom"
    #Make a list of new chromosome objects, which are randomized by default
    genome.genomeList = [GeneAngles() for i in range(genome.getListSize())]


# ===========================================================================================
def ChromosomeInitializatorUseOldPopulation(genome, **args):
    """ Initializator that takes old individuals instead of new ones.
    """
    #   print "ChromosomeInitializatorUseOldPopulation"
    #Pick an old individual using roulette wheel
    old_pop = genome.getParam("old_population")
    old_pop_ID = genome.getParam("old_population_ID")
    old_individual = Selectors.GRouletteWheel(old_pop, popID=old_pop_ID)
    if len(old_individual[0].angles) != len(instrument.inst.angles):
        print("The number of angles in the goniometer has changed, so copying the population is impossible. Re-starting from scratch.")
        #We create a random one
        genome.randomize()
    else:
        #Copy all the genes
        old_individual.copy(genome, keep_list_size=True)


# ===========================================================================================
def ChromosomeMutatorRandomize(genome, **args):
    """ Mutator for a chromosome. Changes one gene to random values."""
    if args["pmut"] <= 0.0: return 0 #No mutants?
    listSize = len(genome)
    mutations = args["pmut"] * (listSize)
    global op #@type op OptimizationParameters

    if mutations < 1.0:
        mutations = 0
        for it in range(listSize):
            if crystalplan.pyevolve.Util.randomFlipCoin(args["pmut"]):
                if op.mutate_by_nudging:
                    genome[it].nudge(op.nudge_amount)
                else:
                    genome[it].mutate()

                mutations += 1
    else:
        for it in range(int(round(mutations))):
            which_gene = random.randint(0, listSize-1)
            if op.mutate_by_nudging:
                genome[which_gene].nudge(op.nudge_amount)
            else:
                genome[which_gene].mutate()
    return int(mutations)


# ===========================================================================================
def ChromosomeMutatorRandomizeAll(genome, **args):
    """ Mutator for a chromosome. Completely randomizes
    the individual."""
    pmut = args["pmut"]
    if pmut <= 0.0: return 0 #No mutants ever
    #Completely mutate only this % of the population
    if crystalplan.pyevolve.Util.randomFlipCoin(pmut):
        for i in range(len(genome)):
            genome[i].mutate()
        return 1
    return 0


# ===========================================================================================
def ChromosomeMutatorRandomizeWorst(genome, **args):
    """ Mutator for a chromosome.
    Finds the orientation giving the most redundant peaks, and randomizes it.
    """
    pmut = args["pmut"]
    if pmut <= 0.0: return 0 #No mutants?

    if not hasattr(genome, 'unique_measurements') or genome.unique_measurements is None:
        #print "ChromosomeMutatorRandomizeWorst: Error: Can't find worst gene list."
        return 0

    #Do the given # of mutations, but flip a coin if non-integer
    num_mutations = int(pmut)
    if pmut - num_mutations > 0:
        if crystalplan.pyevolve.Util.randomFlipCoin(pmut - num_mutations):
            num_mutations += 1
    if num_mutations >= len(genome):
        num_mutations = len(genome)

    #Okay, now we need to look at each orientation to see which one is most redundant
    if num_mutations == 1:
        #--- Just one mutation ---
        global op #@type op OptimizationParameters
        if op.worst_gene_location_randomizer > 0:
            #Possibly move the single mutation around
            offset = int(np.round(np.abs(np.random.normal(scale=op.worst_gene_location_randomizer))))
            if offset >= len(genome):
                offset = len(genome)-1
        else:
            offset = 0

        worst_genes = [genome.unique_measurements[offset][1]]

    else:
        #--- Just do the n-th worst ones ----

        #This is the index of the n-th entry in the # of unique measurements (the worst one)
        worst_genes = [x[1] for x in genome.unique_measurements[0:num_mutations]]

    #We randomize these bad genes
    for bad_gene in worst_genes:
        genome[bad_gene] = GeneAngles()

    return int(num_mutations)



# ===========================================================================================
def ChromosomeCrossoverSinglePoint(genome, **args):
    """ The Single Point crossover
    """
    sister = None
    brother = None
    gMom = args["mom"]
    gDad = args["dad"]

    if len(gMom) == 1:
      crystalplan.pyevolve.Util.raiseException("The 1D List has one element, can't use the Single Point Crossover method !", TypeError)

    cut = random.randint(1, len(gMom)-1)
    if args["count"] >= 1:
      sister = gMom.clone()
      sister.resetStats()
      #Make copies of each gene! Otherwise you are just copying references
      for x in range(cut, len(sister)):
        sister[x] = copy.deepcopy(gDad[x])

    if args["count"] == 2:
      brother = gDad.clone()
      brother.resetStats()
      #Make copies of each gene! Otherwise you are just copying references
      for x in range(cut, len(brother)):
        brother[x] = copy.deepcopy(gMom[x])

    return (sister, brother)


#-----------------------------------------------------------------------------------------------
def get_angles(genome):
    """Extract the list of lists of angles from the genome; for use by eval_func"""
    global op #@type op OptimizationParameters
    #@type instr Instrument
    instr = instrument.inst
    exp = experiment.exp
    
    num_positions = len(genome)
    umatrix = exp.crystal.get_u_matrix()
    
    #Create a new of positions
    positions = []

    for i in range(num_positions):
        #angles = chromosome[i*num_angles:(i+1)*num_angles]
        angles = genome[i].angles
        #Only add it if the angles are allowed.
        if instr.goniometer.are_angles_allowed(angles):
            positions.append(  instrument.PositionCoverage(angles, coverage=None, sample_U_matrix=umatrix) )
        else:
            positions.append( None )

    return positions

#-----------------------------------------------------------------------------------------------
def eval_func(genome, verbose=False):
    """Fitness evaluation function for a chromosome in coverage optimization."""
    global op #@type op OptimizationParameters

    positions = get_angles(genome)
    # Copy
    all_positions = list(positions)
    
    if op.fixed_orientations:
        # Append the fixed positions?
        all_positions += op.fixed_orientations_list

    #@type exp Experiment
    exp = experiment.exp
    #Calculate (this calculates the stats)
    exp.recalculate_reflections(all_positions, calculation_callback=None)
    #Calculate the stats with edge avoidance if an option
    exp.calculate_reflection_coverage_stats(op.avoid_edges, op.edge_x_mm, op.edge_y_mm)

    if op.avoid_edges:
        #Use this fraction
        if op.use_symmetry:
            coverage = exp.reflection_stats_adjusted_with_symmetry.measured * 1.0 / exp.reflection_stats_adjusted_with_symmetry.total
        else:
            coverage = exp.reflection_stats_adjusted.measured * 1.0 / exp.reflection_stats_adjusted.total

    else:
        #No edge avoidance

        #Return the measured fraction
        if op.use_symmetry:
            coverage = exp.reflection_stats_with_symmetry.measured * 1.0 / exp.reflection_stats_with_symmetry.total
        else:
            coverage = exp.reflection_stats.measured * 1.0 / exp.reflection_stats.total


    #----- Now we determine the least useful measurements ------
    positions_id = [id(x) for x in positions]

    #Initialize a dictionary with the measurement redundancy
    unique_measurements = [0]*len(positions_id)
    poscovid_map = {}
    for (i, poscovid) in enumerate(positions_id):
        poscovid_map[poscovid] = i

    if op.use_symmetry:
        #Do a check using symmetry
        for refl in exp.reflections: #@type refl Reflection
            if refl.is_primary and refl.times_measured(None, add_equivalent_ones=op.use_symmetry) == 1:
                #Non-redundant measurement
                poscovid = refl.get_all_measurements()[0][0]
                # Ignore measurements from the fixed orientations
                if poscovid in positions_id:
                    #Find the index in positions list, add 1
                    unique_measurements[poscovid_map[poscovid]] += 1

    else:
        #Check without considering symmetry
        for refl in exp.reflections: #@type refl Reflection
            #If we're using symmetry, skip the check for non-primary beams.
            if len(refl.measurements)==1:
                #Non-redundant measurement
                poscovid = refl.measurements[0][0]
                # Ignore measurements from the fixed orientations
                if poscovid in positions_id:
                    #Find the index in positions list, add 1
                    unique_measurements[poscovid_map[poscovid]] += 1

    #Sort them by the # of unique measurements
    decorated = list(zip(unique_measurements, list(range(len(positions_id)))))
    decorated.sort()

    #Save the sorted list of (unique_measurements, index into the list of genes)
    genome.unique_measurements = decorated
    #Save the coverage value
    genome.coverage = coverage

    if verbose:
        print("Fitness: had %3d positions, score was %7.3f" % (len(positions), coverage))

    #Score is equal to the coverage
    score = coverage
    invalid_positions = len(genome)-len(all_positions)
    if invalid_positions > 0:
        #There some invalid positions. Penalize the score
        score -= (1.0 * invalid_positions) / len(genome)
        if score < 0: score = 0

    return score




#-----------------------------------------------------------------------------------------------
def eval_func_volume(genome, verbose=False):
    """Fitness evaluation function for a chromosome in coverage optimization.
    This one uses the volume coverage."""
    global op #@type op OptimizationParameters
    #@type instr Instrument
    instr = instrument.inst
    instr.verbose = False

    positions = get_angles(genome)
    # Copy
    all_positions = list(positions)
    
    if op.fixed_orientations:
        # Append the fixed positions?
        all_positions += op.fixed_orientations_list

    #Calculate everything
    instr.positions = []
    pd = {}
    for poscov in all_positions: #@type poscov PositionCoverage
        new_poscov = instr.simulate_position(poscov.angles, poscov.sample_U_matrix, use_multiprocessing=False)
        pd[id(new_poscov)] = True

    #@type exp Experiment
    exp = experiment.exp

    #Set all the parameters for evaluation
    #Don't add a trial position
    exp.params[experiment.PARAM_TRY_POSITION] = None
    #Using symmetry is an option when starting optimization.
    exp.params[experiment.PARAM_SYMMETRY] = experiment.ParamSymmetry(op.use_symmetry)
    #All detectors
    exp.params[experiment.PARAM_DETECTORS] = experiment.ParamDetectors([True]*len(instr.detectors))
    #All positions
    exp.params[experiment.PARAM_POSITIONS] = experiment.ParamPositions(pd)
    #Don't invert
    exp.params[experiment.PARAM_INVERT] = None
    #Don't slice
    exp.params[experiment.PARAM_SLICE] = None

    #Calculate (this calculates the stats)
    exp.calculate_coverage(None, None)

    #This is the stat
    coverage = exp.overall_coverage / 100.0

    #Save the sorted list of (unique_measurements, index into the list of genes)
    genome.unique_measurements = None

    #Save the coverage value
    genome.coverage = coverage

    if verbose:
        print("Fitness: had %3d positions, score was %7.3f" % (len(positions), coverage))

    #Score is equal to the coverage
    score = coverage
    invalid_positions = len(genome)-len(all_positions)
    if invalid_positions > 0:
        #There some invalid positions. Penalize the score
        score -= (1.0 * invalid_positions) / len(genome)
        if score < 0: score = 0

    return score


#-----------------------------------------------------------------------------------------------
def termination_func(ga_engine):
    """Termination function for G.A. terminates evolution when
    the desired fitness (coverage) is reached."""
    global op #@type op OptimizationParameters
    best_score = ga_engine.bestIndividual().score
    #When you reach the desired coverage (in %) you are done.
    return best_score * 100.0 >= op.desired_coverage
    


#-----------------------------------------------------------------------------------------------
def set_changeable_parameters(optim_params, ga):
    """Set in the GA engine the parameters that can change generation from generation.
    
    Parameters:
        op: OptimizationParameters instance.
        ga: GA engine instance."""
    #@type op OptimizationParameters
    #@type ga GSimpleGA

    #Set the GA parameters from the configuration variable
    if optim_params.mutation_rate >= 0: ga.setMutationRate(optim_params.mutation_rate)
    if optim_params.pre_mutation_rate >= 0: ga.setPreMutationRate(optim_params.pre_mutation_rate)
    if optim_params.crossover_rate >= 0: ga.setCrossoverRate(optim_params.crossover_rate)
    #Set the multiprocessing. full_copy=True because we change the individual!
    ga.setMultiProcessing(optim_params.use_multiprocessing, full_copy=True, number_of_processes=optim_params.number_of_processors)
    if optim_params.max_generations > 0: ga.setGenerations(optim_params.max_generations)
    ga.setElitism(optim_params.elitism)
    if optim_params.elitism_replacement > 0: ga.setElitismReplacement(optim_params.elitism_replacement)


#-----------------------------------------------------------------------------------------------
def run_optimization(optim_params, step_callback=None):
    """Perform GA optimization of detector coverage. Is meant to be run
    within a background thread, but can run directly.

    Parameters:
        optim_params: OptimizationParameters object with the parameters
        step_callback: function called after every generation, that
            returns True to abort the optimization.
    """
    global op #@type op OptimizationParameters
    op = optim_params

    #The instrument to use
    instr = instrument.inst
    exp = experiment.exp
    exp.verbose = False

    # Genome instance, list of list of angles
    genome = ChromosomeAngles( op.number_of_orientations )

    # Save the fixed orientations at the start of it
    if op.fixed_orientations:
        # Copy the list
        op.fixed_orientations_list = list(instr.positions)

    # In general, we want to init 
    skip_initializer = False

    #Make the initializator
    genome.initializator.set(ChromosomeInitializatorRandom)

    # But we may use a different way?    
    if op.use_old_population:
        if op.population == len(op.old_population) and (op.old_population[0].listSize != op.number_of_orientations):
            skip_initializer = True
            print("Population size and number of orientations are identical. Using the old population as starting point.")
        else:
            print("Population size and/or number of orientations are different. Will generate new population, picked randomly from the old one.")
            #Save the population and a random ID as parameters
            genome.setParams( old_population=op.old_population, old_population_ID=random.randint(0, 10000000) )
            genome.initializator.set(ChromosomeInitializatorUseOldPopulation)

    #Set the pre- and pos-mutators
    genome.premutator.set(ChromosomeMutatorRandomizeWorst)

    genome.mutator.set(ChromosomeMutatorRandomize)

    #The crossover - uniform (swapping elements)
    genome.crossover.set(ChromosomeCrossoverSinglePoint)
    genome.crossover.set(Crossovers.G1DListCrossoverUniform)

    # The evaluator function (evaluation function)
    if op.use_volume:
        genome.evaluator.set(eval_func_volume)
    else:
        genome.evaluator.set(eval_func)

    # Genetic Algorithm Instance
    #@type ga GSimpleGA
    ga = GSimpleGA.GSimpleGA(genome)

    #Fixed settings
    #We want to maximize the score
    ga.setMinimax(Consts.minimaxType["maximize"])
    ga.setPopulationSize(optim_params.population)
    ga.setSortType(crystalplan.pyevolve.Consts.sortType["scaled"])
    # Set the Roulette Wheel selector method
    ga.selector.set(Selectors.GRouletteWheel)

    # If keep_going, then use the old population that was saved instead.
    if op.use_old_population and skip_initializer:
        ga.internalPop = op.old_population
        # Clear the process pool to re-initialize it when running in multiple processes
        ga.internalPop.proc_pool = None 
        
    #Changeable settings. Also copies the individuals to the copies for multiprocessing
    set_changeable_parameters(op, ga)

    #This is the function that can abort the progress.
    if not step_callback is None:
        ga.stepCallback.set(step_callback)
        
    #And this is the termination function
    ga.terminationCriteria.set(termination_func)
        
    freq_stats = 0
    if __name__ == "__main__": freq_stats = 1
    (best, aborted, converged) = ga.evolve(freq_stats=freq_stats, skip_initialize=skip_initializer)

    ga.getPopulation().sort()

    exp.verbose = True

    return (ga, aborted, converged)



def print_pop(ga_engine, *args):
    return
    for x in ga_engine.getPopulation():
        print("score %7.3f; coverage %7.3f, %s" % (x.score, x.coverage, x.genomeList))


if __name__ == "__main__":
    #Inits
    instrument.inst = instrument.Instrument("../instruments/TOPAZ_geom_all_2011.csv")
    instrument.inst.set_goniometer(goniometer.TopazInHouseGoniometer())
    
    # Create a default position of 0,0,0
    instrument.inst.positions = [PositionCoverage([0.0, 0.0, 0.0], None, np.identity(3)), PositionCoverage([1.0, 0.0, 0.0], None, np.identity(3))]
                                                  
    experiment.exp = experiment.Experiment(instrument.inst)
    exp = experiment.exp
    exp.initialize_reflections()
    exp.verbose = False
    
    
    # Go through a bunch of cases
    for use_multiprocessing in [True, False]:
        for fixed_orientations in [True, False]:
            for use_volume in [False]: 

                #Run
                op=OptimizationParameters()
                op.desired_coverage = 85
                op.number_of_orientations = 4
                op.mutation_rate = 0.02
                op.crossover_rate = 0.1
                op.pre_mutation_rate = 1.5
                op.use_symmetry = False
                op.max_generations = 5
                op.population = 10
                op.use_multiprocessing = use_multiprocessing
                op.use_volume = use_volume
                
                op.fixed_orientations = fixed_orientations
                op.use_old_population = False
            
                (ga, a1, a2) = run_optimization( op, print_pop)
                
                
                if True:
                    #Keep going!
                    op.use_old_population = True
                    op.add_trait("old_population", ga.getPopulation())
                    op.population = 10
                    op.number_of_orientations = 4
                    (ga, a1, a2) = run_optimization( op, print_pop)
                    
                    #Keep going, changing pop size
                    op.use_old_population = True
                    op.add_trait("old_population", ga.getPopulation())
                    op.population = 12
                    op.number_of_orientations = 4
                    (ga, a1, a2) = run_optimization( op, print_pop)
                    
                    # Change the number of orientations?
                    op.use_old_population = True
                    op.add_trait("old_population", ga.getPopulation())
                    op.population = 12
                    op.number_of_orientations = 6
                    (ga, a1, a2) = run_optimization( op, print_pop)
    
   
                print("----------best-----------", ga.bestIndividual())
                print("best coverage = ", ga.bestIndividual().coverage)

    
