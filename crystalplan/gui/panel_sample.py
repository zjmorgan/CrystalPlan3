#Boa:FramePanel:PanelSample
"""
Panel in the main window to set sample crystal characteristics.
"""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- General Imports ---
import wx
import time
import numpy as np
import copy

#--- GUI Imports ---
from crystalplan.gui import dialog_edit_crystal
from crystalplan.gui import gui_utils
from crystalplan.gui import display_thread

#--- Traits imports ---
from traits.api import HasTraits,Int,Float,Str,String,Property,Bool, List, Tuple, Array
from traitsui.api import View,Item,Group,Label,Heading, Spring, Handler, TupleEditor, TabularEditor, ArrayEditor, TextEditor, CodeEditor
from traitsui.menu import OKButton, CancelButton,RevertButton
from traitsui.menu import Menu, Action, Separator

#--- Model Imports ---
from crystalplan import model
from crystalplan.model.crystals import Crystal

#=========================================================
#=========================================================
#=========================================================
[wxID_PANELSAMPLE, wxID_PANELSAMPLEBUTTONAPPLYRANGE, 
 wxID_PANELSAMPLEBUTTONEDITCRYSTAL, wxID_PANELSAMPLEBUTTONREVERTRANGE, 
 wxID_PANELSAMPLESTATICLINE1, wxID_PANELSAMPLESTATICTEXTRANGEHEADER, 
] = [wx.NewId() for _init_ctrls in range(6)]

#=========================================================
class HKLRangeSettings(HasTraits):
    """Simple class, with Traits, to set range in hkl."""
    h_range = Array( shape=(1,2), dtype=Int)
    k_range = Array( shape=(1,2), dtype=Int)
    l_range = Array( shape=(1,2), dtype=Int)
    automatic = Bool(True)
    limit_to_sphere = Bool(False)

    view = View( Item("h_range", enabled_when="not automatic"), Item("k_range", enabled_when="not automatic"), Item("l_range", enabled_when="not automatic"),
            Item("automatic", label="Automatically fit to experiment's min d-spacing?"),
            Item("limit_to_sphere", label="Limit to a sphere of radius corresponding to d_min?")
            )

    def __init__(self, exp, *args, **kwargs):
        """Constructor, read in the range values from the experiment exp."""
        HasTraits.__init__(self, *args, **kwargs)
        self.read_from_exp(exp)

    def read_from_exp(self, exp):
        """Read in the ranges from an Experiment instance. """
        self.h_range = np.array( exp.range_h ).reshape(1,2)
        self.k_range = np.array( exp.range_k ).reshape(1,2)
        self.l_range = np.array( exp.range_l ).reshape(1,2)
        self.automatic = exp.range_automatic
        self.limit_to_sphere = exp.range_limit_to_sphere

    def set_in_exp(self, exp):
        """Sets the ranges in an Experiment instance. """
        exp.range_h = tuple(self.h_range.flatten().astype(int))
        exp.range_k = tuple(self.k_range.flatten().astype(int))
        exp.range_l = tuple(self.l_range.flatten().astype(int))
        exp.range_automatic = self.automatic
        exp.range_limit_to_sphere = self.limit_to_sphere

    def is_valid(self):
        """Return True if the values entered make sense."""
        #The higher bound needs to be bigger for each.
        return self.automatic or \
                ((self.h_range[0,1] >= self.h_range[0,0]) and \
                (self.k_range[0,1] >= self.k_range[0,0]) and \
                (self.l_range[0,1] >= self.l_range[0,0]))

    def is_too_many(self):
        """Count the reflections in this range, warn if there are too many.

        Returns:
            bool: true if the number of reflections given by the selection is very large.
            n: integer, number of reflections that will be shown.
        """
        if self.automatic:
            #Count (estimate) automatic peaks
            n = model.experiment.exp.automatic_hkl_range(check_only=True)
        else:
            #Specified range
            n = (self.h_range[0,1]-self.h_range[0,0]+1) * \
                (self.k_range[0,1]-self.k_range[0,0]+1) * \
                (self.l_range[0,1]-self.l_range[0,0]+1)
        return ((n > 1e5), int(n))








#=========================================================
class PanelSample(wx.Panel):
    def _init_coll_boxSizerRangeButtons_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonApplyRange, 0, border=0, flag=0)
        parent.Add(wx.Size(16, 8), border=0, flag=0)
        parent.Add(self.buttonRevertRange, 0, border=0, flag=0)

    def _init_coll_boxSizerAll_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonEditCrystal, 0, border=0,
              flag=wx.ALIGN_CENTER)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticLine1, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextRangeHeader, 0, border=0, flag=0)
        parent.Add(self.staticTextRangeHeader2, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.boxSizerRangeButtons, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=wx.EXPAND)
        parent.Add(self.staticLine2, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)

    def _init_sizers(self):
        # generated method, don't edit
        self.boxSizerAll = wx.BoxSizer(orient=wx.VERTICAL)

        self.boxSizerRangeButtons = wx.BoxSizer(orient=wx.HORIZONTAL)

        self._init_coll_boxSizerAll_Items(self.boxSizerAll)
        self._init_coll_boxSizerRangeButtons_Items(self.boxSizerRangeButtons)

        self.SetSizer(self.boxSizerAll)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Panel.__init__(self, id=wxID_PANELSAMPLE, name='PanelSample',
              parent=prnt, pos=wx.Point(647, 243), size=wx.Size(419, 467),
              style=wx.TAB_TRAVERSAL)
        self.SetClientSize(wx.Size(419, 467))

        self.buttonEditCrystal = wx.Button(id=wxID_PANELSAMPLEBUTTONEDITCRYSTAL,
              label='  Edit Crystal Parameters  ', name='buttonEditCrystal',
              parent=self, pos=wx.Point(117, 8), style=0)
        self.buttonEditCrystal.Bind(wx.EVT_BUTTON,
              self.OnButtonEditCrystalButton,
              id=wxID_PANELSAMPLEBUTTONEDITCRYSTAL)

        self.staticTextRangeHeader = wx.StaticText(id=wxID_PANELSAMPLESTATICTEXTRANGEHEADER,
              label='Enter the range of h, k, and l values to calculate:',
              name='staticTextRangeHeader', parent=self, pos=wx.Point(0, 45),
              size=wx.Size(371, 17), style=0)
        self.staticTextRangeHeader.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL,
              wx.BOLD, False, 'Sans'))

        self.staticTextRangeHeader2 = wx.StaticText(
              label='Values are inclusive',
              name='staticTextRangeHeader2', parent=self, pos=wx.Point(0, 45),
              size=wx.Size(371, 17), style=0)

        self.buttonApplyRange = wx.Button(id=wxID_PANELSAMPLEBUTTONAPPLYRANGE,
              label='  Apply New Range  ', name='buttonApplyRange', parent=self,
              pos=wx.Point(0, 78), style=0)
        self.buttonApplyRange.Bind(wx.EVT_BUTTON, self.OnButtonApplyRangeButton,
              id=wxID_PANELSAMPLEBUTTONAPPLYRANGE)

        self.buttonRevertRange = wx.Button(id=wxID_PANELSAMPLEBUTTONREVERTRANGE,
              label='  Revert  ', name='buttonRevertRange', parent=self,
              pos=wx.Point(193, 78), style=0)
        self.buttonRevertRange.Bind(wx.EVT_BUTTON,
              self.OnButtonRevertRangeButton,
              id=wxID_PANELSAMPLEBUTTONREVERTRANGE)

        self.staticLine1 = wx.StaticLine(id=wxID_PANELSAMPLESTATICLINE1,
              name='staticLine1', parent=self, pos=wx.Point(0, 115),
              size=wx.Size(419, 2), style=0)

        self.staticLine2 = wx.StaticLine(name='staticLine2', parent=self, pos=wx.Point(0, 115), size=wx.Size(419, 2), style=0)

        self._init_sizers()


    def __init__(self, parent):
        self._init_ctrls(parent)

        vector_format = "%.3f"
        #Make a simple, mostly read-only view for the crystal
        self.crystal_view = View(
            Item("name", label="Crystal Name"),
            Item("description", label="Description:", editor=TextEditor(multi_line=True)),
            Item("lattice_lengths_arr", label="Lattice sizes (Angstroms)", format_str="%.3f", style='readonly'),
            Item("lattice_angles_deg_arr", label="Lattice angles (degrees)", format_str="%.3f", style='readonly'),
            Item("ub_matrix", label="Sample's UB Matrix", style='readonly', format_str="%9.5f"),
            Item("point_group_name", label="Point Group", style='readonly'),
            Item("reflection_condition_name", label="Reflection Condition", style='readonly'),
#            Item("recip_a", label="a*", style='readonly'),
#            Item("recip_b", label="b*", style='readonly'),
#            Item("recip_c", label="c*", style='readonly'),
            Item("a", label="a vector", format_str=vector_format, style='readonly'),
            Item("b", label="b vector", format_str=vector_format, style='readonly'),
            Item("c", label="c vector", format_str=vector_format, style='readonly'),
            resizable=True
            )


        #Create the range settings object using the global experiment
        self.range_settings = HKLRangeSettings(model.experiment.exp)
        self.range_control = self.range_settings.edit_traits(parent=self, kind='subpanel').control
        self.boxSizerAll.Insert(8, self.range_control, 0, border=1, flag=wx.EXPAND)

        #This'll create the control
        self.crystal_control = None
        self.Refresh()

    #---------------------------------------------------------------------------
    def Refresh(self):
        #Remove the existing one
        if not self.crystal_control is None:
            self.boxSizerAll.Remove(self.crystal_control)
            self.crystal_control.Destroy()

        #Replace with the current crystal object
        crystal = model.experiment.exp.crystal
        self.crystal_control = crystal.edit_traits(parent=self, view=self.crystal_view, kind='subpanel').control
        #Put it in there
        self.boxSizerAll.Insert(0, self.crystal_control, 0, border=1, flag=wx.EXPAND)
        self.GetSizer().Layout()
        #Also update the range settings
        self.range_settings.read_from_exp(model.experiment.exp)
        

    #------------------------------------------------------------------
    def update_current(self):
        gon = copy.copy(model.instrument.inst.goniometer)
        self.current_gon_copy = gon
        if not self.panel.currentControl is None:
            #Remove the existing one
            self.panel.boxSizerAll.Remove(self.panel.currentControl)
            self.panel.currentControl.Destroy()

        if gon is None:
            self.panel.staticTextCurrentGonio.SetLabel("None selected!")
        else:
            self.panel.staticTextCurrentGonio.SetLabel('') #(gon.name)
            self.panel.currentControl = self.current_gon_copy.edit_traits(parent=self.panel, kind='subpanel').control
            self.panel.boxSizerAll.Insert(2, self.panel.currentControl, 0, flag=wx.EXPAND | wx.SHRINK)

        self.panel.boxSizerAll.Layout()


    #---------------------------------------------------------------------------
    def apply_crystal_range(self):
        #Apply the range to the experiment
        self.range_settings.set_in_exp(model.experiment.exp)

        #Make a progress bar
        # self.count = 4
        max = len(model.instrument.inst.positions)+2 #Steps in calculation
        self.count = max
        self.prog_dlg = wx.ProgressDialog( "Reflection Calculation Progress",        
                                          "Initializing reflections for sample.              ",
            max, style = wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME |
                         wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME | wx.PD_AUTO_HIDE)
        self.prog_dlg.Update(self.count)

        #Initialize the peaks here.
        model.experiment.exp.initialize_reflections()

        #In automatic mode, lets read out what the hkl range was
        if self.range_settings.automatic:
            self.range_settings.read_from_exp(model.experiment.exp)

        #Recalculate peaks here.
        model.experiment.exp.recalculate_reflections(None, calculation_callback=self._calculation_progress_report)
        
        #Clean up progress dialog
        self.prog_dlg.Destroy()

        #Manually send message to redraw
        model.messages.send_message(model.messages.MSG_EXPERIMENT_REFLECTIONS_CHANGED)
        
    #---------------------------------------------------------------------------
    def _calculation_progress_report(self, poscov):
        """Callback to show progress during a calculation."""
        self.count += 1
        self.prog_dlg.Update(self.count, "Calculating reflections for orientation %s..." % (model.instrument.inst.make_angles_string(poscov.angles)))


    #---------------------------------------------------------------------------
    def OnButtonEditCrystalButton(self, event):
        """Clicking the button to change the crystal settings."""
        old_U = model.experiment.exp.crystal.get_u_matrix()
        
        if dialog_edit_crystal.show_dialog(self, model.experiment.exp.crystal):
            self.OnReturningFromEditCrystal(old_U)

        event.Skip()

    #---------------------------------------------------------------------------
    def OnReturningFromEditCrystal(self, old_U):
        """Call when changing the crystal, either from the button or from loading a UB file.
        Model.exp.crystal needs to have changed before calling
        """
        #Whenever the crystal changes, you need a new symmetry map.
        model.experiment.exp.initialize_volume_symmetry_map()

        #User clicked okay, something (proably) changed
        new_U = model.experiment.exp.crystal.get_u_matrix()
        if not np.allclose(old_U, new_U):
            #The sample mounting U changed, so we need to recalc all the 3D volume coverage
            gui_utils.do_recalculation_with_progress_bar(new_U)

        #Send message signaling a redraw of volume plots
        display_thread.handle_change_of_qspace(changed_sample_U_matrix=new_U)

        #Now handle the reflections, and warn if the auto-range is huge...
        (b,n) = self.range_settings.is_too_many()
        if b:
            dlg =  wx.MessageDialog(self, "The number of reflections given by this range, %s, is very large. Are you sure?\nIf you click no, a default range of -5 to +5 HKL will be used instead, but you can increase the range later." % gui_utils.print_large_number(n),
                                    "Too Many Reflections", wx.YES_NO | wx.ICON_INFORMATION)
            res = dlg.ShowModal()
            dlg.Destroy()
            if res != wx.ID_YES:
                #Disable automatic if its on; put on smaller numbers.
                self.range_settings.automatic = False
                self.range_settings.h_range = np.array( [-5,5] ).reshape(1,2)
                self.range_settings.k_range = np.array( [-5,5] ).reshape(1,2)
                self.range_settings.l_range = np.array( [-5,5] ).reshape(1,2)

        #Update the hkl range settings, especially for automatic settings
        self.apply_crystal_range()



    #---------------------------------------------------------------------------
    def OnButtonApplyRangeButton(self, event):
        #Are they okay?
        if not self.range_settings.is_valid():
            wx.MessageDialog(self, "Invalid entries in the ranges. Make sure the higher bound is >= the lower bound.", "Can't apply ranges", wx.OK | wx.ICON_ERROR).ShowModal()
            return
        (b,n) = self.range_settings.is_too_many()
        if b:
            dlg =  wx.MessageDialog(self, "The number of reflections given by this range, %s, is very large. Are you sure?" % gui_utils.print_large_number(n),
                                    "Too Many Reflections", wx.YES_NO | wx.ICON_INFORMATION)
            res = dlg.ShowModal()
            dlg.Destroy()
            if res != wx.ID_YES:
                self.range_settings.automatic = False #Disable automatic if its on
                return
        #Do it!

        self.apply_crystal_range()
        event.Skip()


    def OnButtonRevertRangeButton(self, event):
        #Go back to what is saved in there.
        self.range_settings.read_from_exp(model.experiment.exp)
        event.Skip()







if __name__=="__main__":
    model.crystals._initialize()
    #Test routine
    model.instrument.inst = model.instrument.Instrument()
    model.experiment.exp = model.experiment.Experiment(model.instrument.inst)
    from . import gui_utils
    (app, pnl) = gui_utils.test_my_gui(PanelSample)
    app.MainLoop()

    
