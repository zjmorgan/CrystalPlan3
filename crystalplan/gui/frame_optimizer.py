#Boa:Frame:FrameOptimizer
"""
FrameOptimizer: frame with GUI for automatically creating an experiment plan
by optimizing coverage using a genetic algorithm.
"""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id: panel_goniometer.py 1143 2010-04-07 20:57:45Z 8oz $

import wx
import time
import threading

#--- GUI Imports ----
from crystalplan.gui import display_thread
from crystalplan.gui import gui_utils

#--- Model Imports ----
from crystalplan import model
from crystalplan.model.optimization import OptimizationParameters
from crystalplan import CrystalPlan_version

if __name__=="__main__":
    #Manipulate the PYTHONPATH to put model directly in view of it
    import sys
    sys.path.insert(0, "..")
    


#-------------------------------------------------------------------------------
#------ SINGLETON --------------------------------------------------------------
#-------------------------------------------------------------------------------
_instance = None

def create(parent):
    global _instance
    _instance = FrameOptimizer(parent)
    return _instance

def get_instance(parent):
    """Returns the singleton instance of this frame (window)."""
    global _instance
    if _instance is None:
        return create(parent)
    else:
        return _instance

#================================================================================================
#================================================================================================
class PlotPanel (wx.Panel):
    """The PlotPanel has a Figure and a Canvas. OnSize events simply set a
flag, and the actual resizing of the figure is triggered by an Idle event."""
    def __init__( self, parent, color=None, dpi=None, **kwargs ):
        from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
        from matplotlib.figure import Figure

        # initialize Panel
        if 'id' not in list(kwargs.keys()):
            kwargs['id'] = wx.ID_ANY
        if 'style' not in list(kwargs.keys()):
            kwargs['style'] = wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Panel.__init__( self, parent, **kwargs )

        # initialize matplotlib stuff
        self.figure = Figure( None, dpi )
        self.canvas = FigureCanvasWxAgg( self, -1, self.figure )
        self.SetColor( color )

        self._resizeflag = False

        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)

    def SetColor( self, rgbtuple=None ):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ).Get()
        clr = [c/255. for c in rgbtuple]
        self.figure.set_facecolor( clr )
        self.figure.set_edgecolor( clr )
        self.canvas.SetBackgroundColour( wx.Colour( *rgbtuple ) )

    def _onSize( self, event ):
        self._resizeflag = True

    def _onIdle( self, evt ):
        if self._resizeflag:
            self._resizeflag = False
            self.canvas.SetSize( self.GetSize() )

    def draw(self, *args, **kwargs):
        pass # abstract, to be overridden by child classes
        if not hasattr( self, 'subplot' ):
            self.subplot = self.figure.add_subplot( 111 )
        clr = [0.5, 0.5, 0.5]
        self.subplot.plot( [1,2,3,4], [-5,12,3,45], color=clr )


#================================================================================================
class PlotPanelGAStats(PlotPanel):
    """Panel that draws the GA generational stats."""
    def __init__( self, *args, **kwargs ):
        PlotPanel.__init__(self, *args, **kwargs)

    def draw(self, generations):
        """Make a plot of the raw score with error bars."""
        if not hasattr( self, 'subplot' ):
            self.subplot = self.figure.add_subplot( 111 )
            
        x = []
        y = []
        yerr_max = []
        yerr_min = []

        #@type it GAStats
        for it in generations:
            x.append(it.generation)
            y.append(it.average)
            ymax = it.best - it.average
            ymin = it.average - it.worst

            yerr_max.append(ymax)
            yerr_min.append(ymin)

        self.subplot.clear()
        if len(x)>0:
            self.subplot.errorbar(x, y, [yerr_min, yerr_max], ecolor="g")
        self.subplot.grid(True)
        self.subplot.set_xlabel('Generation (#)')
        self.subplot.set_ylabel('Coverage Score Min/Avg/Max')
        self.subplot.set_title("Evolution of coverage")
        #Signal refresh?
        self._resizeflag = True


#================================================================================================
class GAData():
    """Simple class holding data about each GA generation."""
    def __init__(self, generation, best, average, worst):
        self.generation = generation
        self.best = best
        self.average = average
        self.worst = worst


#================================================================================================
#================================================================================================
class OptimizationThread(threading.Thread):
    """Thread to run the GA optimization."""
    def __init__ (self, controller):
        threading.Thread.__init__(self)
        self.controller = controller
        self.start() #Start on creation

    def run(self):
        #Just run the optimization
        self.controller.params.optimization_running = True
        try:
            (ga, aborted, converged) = model.optimization.run_optimization(self.controller.params, self.controller.step_callback)
            self.controller.params.optimization_running = False
            #Call the completion function.
            self.controller.complete( ga, aborted, converged )
        except Exception as inst:
            print("Error while running optimization")
            print(inst)
            self.controller.restore_buttons()
        finally:
            self.controller.params.optimization_running = False
            

#================================================================================================
#================================================================================================
#================================================================================================
class OptimizerController():
    """Controller for the coverage optimizer."""

    #--------------------------------------------------------------------
    def __init__(self, frame):
        """Constructor.

        Parameters:
            frame: the FrameOptimizer instance."""
        self.frame = frame
        self.params = OptimizationParameters()
        self.params.optimization_running = False
        self.best = None
        self.best_coverage = 0
        self.average_coverage = 0
        self.best_chromosome = []
        self.currentGeneration = 0
        self.run_thread = None
        self.start_time = 0
        self.last_population = None
        self.generations = []
        self.last_plot_time = time.time()-10
        #Frequency of plotting
        self.plot_time_interval = 1

    #--------------------------------------------------------------------
    def restore_buttons(self):
        """ Restore the button states to the initial value """
        self.frame.buttonStart.Enable(True)
        self.frame.buttonKeepGoing.Enable(False)
        self.frame.buttonApply.Enable(False)
        self.frame.buttonStop.Enable(False)

    #--------------------------------------------------------------------
    def update(self):
        """Update GUI elements to reflect the current status."""
        frm = self.frame #@type frm FrameOptimizer
        if frm is None:
            return
        if self.params.avoid_edges and not self.params.use_volume:
            edges = " (excluding edges)"
        else:
            edges = ""
        #Coverage stats
        frm.staticTextCoverage.SetLabel("Best Coverage%s: %7.2f %%" % (edges, self.best_coverage*100))
        frm.gaugeCoverage.SetValue(self.best_coverage*100)
        frm.staticTextAverage.SetLabel("Average Coverage%s: %7.2f %%" % (edges, self.average_coverage*100))
        frm.gaugeAverage.SetValue(self.average_coverage*100)
        #The generation counter
        maxgen = self.params.max_generations
        frm.gaugeGeneration.SetRange(maxgen)
        frm.gaugeGeneration.SetValue(self.currentGeneration)
        frm.staticTextGeneration.SetLabel("Generation %5d of %5d:" % (self.currentGeneration, maxgen))
        #The individual
        if not self.best is None:
            frm.textStatus.SetValue("Best individual has %7.3f coverage:\n%s" % (self.best.coverage, str(self.best.genomeList)))
            frm.buttonApply.Enable(True)
        else:
            frm.textStatus.SetValue("No best individual")
            frm.buttonApply.Enable(False)
        #The start/stop buttons enabling
        frm.buttonStart.Enable((self.run_thread is None))
        frm.buttonStop.Enable(not (self.run_thread is None))
        #The keep going button
        frm.buttonKeepGoing.Enable( not (self.last_population is None) and (self.run_thread is None) )

    #--------------------------------------------------------------------
    def start(self, event, *args):
        """Start the optimization."""
        self._want_abort = False
        self.start_time = time.time()
        self.init_data()
        #Start the thread
        self.params.use_old_population = False
        self.run_thread = OptimizationThread(self)
        #Set the buttons right away.
        frm = self.frame #@type frm FrameOptimizer
        frm.buttonStart.Enable((self.run_thread is None))
        frm.buttonStop.Enable(not (self.run_thread is None))

        self.frame.staticTextComplete.SetLabel("Optimization started...")
        if not event is None: event.Skip()

    #--------------------------------------------------------------------
    def keep_going(self, event):
        """Continue optimization, using the last saved population."""
        if self.last_population is None:
            wx.MessageDialog(self.frame, "Error! No saved population. You need to start the optimization at least once.").ShowModal()
            return

#        if s:
#            wx.MessageDialog("Number of sample orientations has changed. Cannot keep going with the old population.").ShowModal()
#            return;
        
        if (self.params.population != len(self.last_population)) or (self.last_population[0].listSize != self.params.number_of_orientations):
            wx.MessageDialog(self.frame, "Population size/number of orientations changed. The new population will be selected randomly from the old one, and may not be as good.", style=wx.OK).ShowModal()
        
        self._want_abort = False
        self.start_time = time.time()
        self.init_data()
        
        #Start the thread
        self.params.use_old_population = True
        self.params.add_trait("old_population", self.last_population)
        self.run_thread = OptimizationThread(self)

        #Set the buttons right away.
        frm = self.frame #@type frm FrameOptimizer
        frm.buttonStart.Enable((self.run_thread is None))
        frm.buttonStop.Enable(not (self.run_thread is None))

        self.frame.staticTextComplete.SetLabel("Optimization started...")
        if not event is None: event.Skip()

    #--------------------------------------------------------------------
    def stop(self, event, *args):
        """Stop the optimization."""
        self._want_abort = True
        #Will have to wait for the next generation to stop
        if not event is None: event.Skip()
        
    #--------------------------------------------------------------------
    def close_form(self, event, *args):
        """Call when the form is closing. Abort the thread if it is running."""
        self._want_abort = True
        #Marker to avoid trying to change GUI
        self.frame = None
        #For the singleton
        global _instance
        _instance = None
        if not event is None: event.Skip()




    #--------------------------------------------------------------------
    def init_data(self):
        """Initialize and clear the GA data log."""
        self.generations = []

    #--------------------------------------------------------------------
    def add_data(self, ga):
        """Add one entry to the GA data log."""
        stats = ga.getStatistics()
        self.generations.append( GAData(ga.currentGeneration, stats["rawMax"], stats["rawAve"], stats["rawMin"]) )

    #--------------------------------------------------------------------
    def plot_data(self):
        """Plot whatever the data currently is"""
        self.frame.plotControl.draw(self.generations)
        self.last_plot_time = time.time()


    #--------------------------------------------------------------------
    def complete(self, ga, aborted, converged):
        """Called when the optimization completes.
        
        Parameters:
            ga: the GSimpleGA instance
            aborted: True if the optimization was aborted manually
            converged: True if the criterion was reached.
        """
        if aborted:
            label = "ABORTED - Optimization was aborted before completing!"
        elif converged:
            label = "SUCCESS - Optimization met the coverage criterion!"
        else:
            label = "FAILED - Reached the max. # of generations without enough coverage!"

        self.run_thread = None
        self.add_data(ga)
        #Make sure GUI updates
        wx.CallAfter(self.frame.staticTextComplete.SetLabel, label)
        wx.CallAfter(self.plot_data)
        wx.CallAfter(self.update)

        #Save the population
        self.last_population = ga.getPopulation()

        if self.params.auto_increment and not aborted and not converged:
            print("AUTO INCREMENTING !!!")
            #Try again with 1 more orientation
            self.params.number_of_orientations += 1
            wx.CallAfter(self.keep_going, None)
        else:
            #Done!
            print("Optimization finished in %.3f seconds." % (time.time() - self.start_time))

        
    #--------------------------------------------------------------------
    def step_callback(self, ga, *args):
        """Callback during evolution; used to abort it and to display
        stats."""
        #@type ga GSimpleGA
        op = self.params #@type op OptimizationParameters
        
        #Find the best individual
        self.best = ga.bestIndividual()
        self.best_coverage = self.best.coverage
        #More stats
        stats = ga.getStatistics()
        self.average_coverage = stats["rawAve"]
        #Other stats
        self.currentGeneration = ga.currentGeneration
        #Log the stats too
        self.add_data(ga)
        
        #Adjust settings while going on
        model.optimization.set_changeable_parameters(op, ga)

        #Update gui
        if time.time()-self.last_plot_time > self.plot_time_interval:
            #Enough time has passed, plot the graph
            wx.CallAfter(self.plot_data)
        wx.CallAfter(self.update)
        return self._want_abort






    #--------------------------------------------------------------------
    def apply(self, event, *args):
        """Apply the best results."""
        #TODO: Confirmation message box?
        positions = []

        # Get the angles of the best one
        positions += model.optimization.get_angles(self.best)
            
        print("Applying best individual", self.best)

        #This deletes everything in the list in the instrument
        if not self.params.fixed_orientations:
            del model.instrument.inst.positions[:]
            #Make sure to clear the parameters too, by giving it an empty dict() object.
            display_thread.clear_positions_selected()

        #This function does the calc. and shows a progress bar. Can be aborted too.
        gui_utils.do_calculation_with_progress_bar(positions)

        #GUI update
        model.messages.send_message(model.messages.MSG_POSITION_LIST_CHANGED)
        
        #Add it to the list of selected items
        if len(model.instrument.inst.angles) == 1:
            model.instrument.inst.sort_positions_by(0)
        display_thread.select_position_coverage(model.instrument.inst.positions, update_gui=True)

        if not event is None: event.Skip()

        






#================================================================================================
#================================================================================================
#================================================================================================
[wxID_FRAMEOPTIMIZER, wxID_FRAMEOPTIMIZERbuttonKeepGoing,
 wxID_FRAMEOPTIMIZERBUTTONAPPLY, wxID_FRAMEOPTIMIZERBUTTONSTART, 
 wxID_FRAMEOPTIMIZERBUTTONSTOP, wxID_FRAMEOPTIMIZERGAUGECOVERAGE, 
 wxID_FRAMEOPTIMIZERGAUGEGENERATION, wxID_FRAMEOPTIMIZERPANELPARAMS, 
 wxID_FRAMEOPTIMIZERPANELSTATUS, wxID_FRAMEOPTIMIZERSPLITTERMAIN, 
 wxID_FRAMEOPTIMIZERSTATICLINE1, wxID_FRAMEOPTIMIZERSTATICTEXT1, 
 wxID_FRAMEOPTIMIZERSTATICTEXTCOVERAGE, 
 wxID_FRAMEOPTIMIZERSTATICTEXTGENERATION, 
 wxID_FRAMEOPTIMIZERSTATICTEXTRESULTS, wxID_FRAMEOPTIMIZERTEXTSTATUS, 
] = [wx.NewId() for _init_ctrls in range(16)]

#================================================================================================
class FrameOptimizer(wx.Frame):
    def _init_coll_boxSizerParams_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticText1, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticLine1, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextHelp, 0, border=0, flag=wx.EXPAND)

    def _init_coll_boxSizerStatus_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextResults, 0, border=4, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.textStatus, 1, border=10, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.plotControl, 3, border=10, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHRINK)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextGeneration, 0, border=4, flag=wx.LEFT)
        parent.Add(self.gaugeGeneration, 0, border=10, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)
        parent.Add(wx.Size(8, 8), border=0, flag=wx.EXPAND)
        parent.Add(self.staticTextCoverage, 0, border=4, flag=wx.LEFT)
        parent.Add(self.gaugeCoverage, 0, border=10, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)
        parent.Add(wx.Size(8, 8), border=0, flag=wx.EXPAND)
        parent.Add(self.staticTextAverage, 0, border=4, flag=wx.LEFT)
        parent.Add(self.gaugeAverage, 0, border=10, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextComplete, 0, border=4, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(wx.StaticLine(parent=self.panelStatus), 0, border=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.gridSizerStatusButtons, 0, border=0, flag=wx.CENTER)
        parent.Add(wx.Size(8, 8), border=0, flag=0)

    def _init_coll_boxSizerAll_Items(self, parent):
        # generated method, don't edit

        parent.Add(self.splitterMain, 1, border=8,
              flag=wx.TOP | wx.RIGHT | wx.LEFT | wx.EXPAND)
        parent.Add(wx.Size(16, 16), border=0,
              flag=wx.BOTTOM | wx.TOP | wx.RIGHT | wx.LEFT)

    def _init_coll_gridSizerStatusButtons_Items(self, parent):
        # generated method, don't edit

        parent.Add(self.buttonStart, 0, border=0,
              flag=wx.ALIGN_CENTER_HORIZONTAL)
        parent.Add(self.buttonKeepGoing, 0, border=0,
              flag=wx.ALIGN_CENTER_HORIZONTAL)
        parent.Add(self.buttonStop, 0, border=0, flag=wx.ALIGN_CENTER)
        parent.Add(self.buttonApply, 0, border=0, flag=wx.ALIGN_CENTER)

    def _init_sizers(self):
        # generated method, don't edit
        self.boxSizerAll = wx.BoxSizer(orient=wx.VERTICAL)

        self.boxSizerStatus = wx.BoxSizer(orient=wx.VERTICAL)

        self.boxSizerParams = wx.BoxSizer(orient=wx.VERTICAL)

        self.gridSizerStatusButtons = wx.FlexGridSizer(cols=2, hgap=5, rows=2,
              vgap=4)

        self._init_coll_boxSizerAll_Items(self.boxSizerAll)
        self._init_coll_boxSizerStatus_Items(self.boxSizerStatus)
        self._init_coll_boxSizerParams_Items(self.boxSizerParams)
        self._init_coll_gridSizerStatusButtons_Items(self.gridSizerStatusButtons)

        self.SetSizer(self.boxSizerAll)
        self.panelStatus.SetSizer(self.boxSizerStatus)
        self.panelParams.SetSizer(self.boxSizerParams)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Frame.__init__(self, id=wxID_FRAMEOPTIMIZER, name='FrameOptimizer',
              parent=prnt, pos=wx.Point(976, 171), size=wx.Size(715, 599),
              style=wx.DEFAULT_FRAME_STYLE, title='Automatic Coverage Optimizer')
        self.SetClientSize(wx.Size(900, 800))
        self.Bind(wx.EVT_CLOSE, self.controller.close_form)

        #Little icon
        import os
        icon_file = os.path.join(os.path.dirname(__file__), CrystalPlan_version.icon_file_optimizer)
        self.SetIcon( wx.Icon(icon_file, wx.BITMAP_TYPE_PNG) )

        self.splitterMain = wx.SplitterWindow(id=wxID_FRAMEOPTIMIZERSPLITTERMAIN,
              name='splitterMain', parent=self, pos=wx.Point(8, 8),
              size=wx.Size(699, 575), style=wx.SP_3D)
        # self.splitterMain.SetSashSize(8)
        self.splitterMain.SetSashGravity(0.4)

        self.panelParams = wx.Panel(id=wxID_FRAMEOPTIMIZERPANELPARAMS,
              name='panelParams', parent=self.splitterMain, pos=wx.Point(0, 0),
              size=wx.Size(10, 575), style=wx.TAB_TRAVERSAL)
        self.panelParams.SetBackgroundColour(wx.Colour(246, 246, 235))

        self.panelStatus = wx.Panel(id=wxID_FRAMEOPTIMIZERPANELSTATUS,
              name='panelStatus', parent=self.splitterMain, pos=wx.Point(18,
              0), size=wx.Size(681, 575), style=wx.TAB_TRAVERSAL)
        self.panelStatus.SetBackgroundColour(wx.Colour(235, 246, 245))
        self.splitterMain.SplitVertically(self.panelParams, self.panelStatus)

        self.staticText1 = wx.StaticText(id=wxID_FRAMEOPTIMIZERSTATICTEXT1,
              label='Optimization Parameters:', name='staticText1',
              parent=self.panelParams, pos=wx.Point(0, 8), style=0)
        self.staticText1.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False, 'Sans'))

        self.staticTextHelp = wx.StaticText(id=wx.NewId(), name='staticText1',
              label="""The genetic algorithm attempts to maximize the percentage of measured reflections. Enter the goals and GA parameters above.
DO NOT modify settings in the main window (such as goniometer choice, sample parameters, etc.) while optimization is running, as that will cause problems!!!
Click Apply Results while optimizing to see the current best solution.""",
              parent=self.panelParams, pos=wx.Point(0, 8), style=0)

        self.staticLine1 = wx.StaticLine(id=wxID_FRAMEOPTIMIZERSTATICLINE1,
              name='staticLine1', parent=self.panelParams, pos=wx.Point(0, 33),
              size=wx.Size(419, 2), style=0)

        self.staticTextResults = wx.StaticText(id=wxID_FRAMEOPTIMIZERSTATICTEXTRESULTS,
              label='Current Status:', name='staticTextResults',
              parent=self.panelStatus, pos=wx.Point(0, 8), size=wx.Size(98, 17),
              style=0)

        self.textStatus = wx.TextCtrl(id=wxID_FRAMEOPTIMIZERTEXTSTATUS,
              name='textStatus', parent=self.panelStatus, pos=wx.Point(0, 33),
              style=wx.TE_MULTILINE + wx.TE_READONLY, value=' ')

        self.gaugeGeneration = wx.Gauge(id=wxID_FRAMEOPTIMIZERGAUGEGENERATION,
              name='gaugeGeneration', parent=self.panelStatus, pos=wx.Point(0,
              424), range=100,  style=wx.GA_HORIZONTAL)

        self.staticTextGeneration = wx.StaticText(id=wxID_FRAMEOPTIMIZERSTATICTEXTGENERATION,
              label='Generation Progress:', name='staticTextGeneration',
              parent=self.panelStatus, pos=wx.Point(0, 407), style=0)

        self.gaugeCoverage = wx.Gauge(id=wxID_FRAMEOPTIMIZERGAUGECOVERAGE,
              name='gaugeCoverage', parent=self.panelStatus, pos=wx.Point(0,
              477), range=100,  style=wx.GA_HORIZONTAL)

        self.staticTextCoverage = wx.StaticText(id=wxID_FRAMEOPTIMIZERSTATICTEXTCOVERAGE,
              label='Best Coverage:', name='staticTextCoverage',
              parent=self.panelStatus, pos=wx.Point(0, 460), style=0)

        self.gaugeAverage = wx.Gauge(id=wxID_FRAMEOPTIMIZERGAUGECOVERAGE,
              name='gaugeAverage', parent=self.panelStatus, pos=wx.Point(0,
              477), range=100,  style=wx.GA_HORIZONTAL)

        self.staticTextAverage = wx.StaticText(id=wxID_FRAMEOPTIMIZERSTATICTEXTCOVERAGE,
              label='Average Coverage:', name='staticTextAverage',
              parent=self.panelStatus, pos=wx.Point(0, 460), style=0)

        self.staticTextComplete = wx.StaticText(id=wx.NewId(),
              label='...', name='staticTextComplete',
              parent=self.panelStatus, pos=wx.Point(0, 460), style=0)

        self.buttonKeepGoing = wx.Button(id=wxID_FRAMEOPTIMIZERbuttonKeepGoing,
              label='Keep Going...',
              name='buttonKeepGoing', parent=self.panelStatus,
              pos=wx.Point(380, 513), size=wx.Size(152, 29), style=0)
        self.buttonKeepGoing.Bind(wx.EVT_BUTTON, self.controller.keep_going)
        self.buttonKeepGoing.SetToolTip("Keep optimizing using ~ the last saved population as the starting point.")

        self.buttonStart = wx.Button(id=wxID_FRAMEOPTIMIZERBUTTONSTART,
              label='Start Optimization', name='buttonStart',
              parent=self.panelStatus, pos=wx.Point(93, 513), size=wx.Size(152,
              29), style=0)
        self.buttonStart.SetToolTip('Begin the optimization process in a background thread.')
        self.buttonStart.Bind(wx.EVT_BUTTON, self.controller.start)

        self.buttonStop = wx.Button(id=wxID_FRAMEOPTIMIZERBUTTONSTOP,
              label='Stop!', name='buttonStop', parent=self.panelStatus,
              pos=wx.Point(126, 546), size=wx.Size(85, 29), style=0)
        self.buttonStop.SetToolTip("Abort the Genetic Algorithm search.")
        self.buttonStop.Bind(wx.EVT_BUTTON, self.controller.stop)

        self.buttonApply = wx.Button(id=wxID_FRAMEOPTIMIZERBUTTONAPPLY,
              label='Apply Results', name='buttonApply',
              parent=self.panelStatus, pos=wx.Point(441, 546), size=wx.Size(142,
              29), style=0)
        self.buttonApply.SetToolTip("Set the experiment plan to be the best solution found by the genetic algorithm.")
        self.buttonApply.Bind(wx.EVT_BUTTON, self.controller.apply)

        #--- Plot ---
        self.plotControl = PlotPanelGAStats(self.panelStatus)

        self._init_sizers()

    def __init__(self, parent):
        #The view controller
        self.controller = OptimizerController(self)

        self._init_ctrls(parent)

        #Initial update.
        self.controller.update()
        #Clear axes
        self.controller.plot_data()

        #--- Parameters ----
        self.params_control = self.controller.params.edit_traits(parent=self.panelParams,kind='subpanel').control
        self.boxSizerParams.Insert(2, self.params_control, 0, border=1, flag=wx.EXPAND)
        self.boxSizerParams.Layout()






if __name__ == "__main__":
    from . import gui_utils
    (app, frm) = gui_utils.test_my_gui(FrameOptimizer)
    frm.Raise()
    app.MainLoop()
