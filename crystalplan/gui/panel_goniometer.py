#Boa:FramePanel:PanelGoniometer
"""
PanelGoniometer: a GUI component that shows the user the limits of the angles achievable with the
goniometer.
"""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- General Imports ---
import wx
import copy
from crystalplan.gui import dialog_goniometer_angles

#--- GUI Imports ---
from crystalplan.gui import gui_utils

#--- Model Imports ---
from crystalplan import model

#--- Traits Imports ---
from traits.api import HasTraits,Int,Float,Str,String,Property,Bool, List, Tuple, Array, Enum
from traitsui.api import View,Item,Group,Label,Heading, Spring, Handler, TupleEditor, TabularEditor, ArrayEditor, TextEditor, CodeEditor, ListEditor, TableEditor
from traitsui.menu import OKButton, CancelButton,RevertButton
from traitsui.menu import Menu, Action, Separator


[wxID_PANELGONIOMETER, wxID_PANELGONIOMETERCHOICEGONIO, 
 wxID_PANELGONIOMETERSTATICTEXT1, wxID_PANELGONIOMETERSTATICTEXTDESC, 
 wxID_PANELGONIOMETERSTATICTEXTDESCLABEL, 
 wxID_PANELGONIOMETERstaticTextCurrentGonio,
 wxID_PANELGONIOMETERSTATICTEXTTITLE, 
] = [wx.NewId() for _init_ctrls in range(7)]

class PanelGoniometerController():
    """Controller and view for the PanelGoniometer."""
    selected = None
    
    #------------------------------------------------------------------
    def __init__(self, panel):
        self.panel = panel
        #Select the 1st one by default
        self.selected = model.goniometer.goniometers[0]

    def show_current_gon_copy(self):
        """ Updates the GUI with whatever is in
        self.current_gon_copy """
        if not self.panel.currentControl is None:
            # Remove the existing one
            # self.panel.boxSizerAll.Remove(self.panel.currentControl)
            self.panel.boxSizerAll.Hide(2)
            self.panel.boxSizerAll.Remove(2)
            self.panel.currentControl.Close()

        if self.current_gon_copy is None:
            self.panel.staticTextCurrentGonio.SetLabel("None selected!")
        else:
            self.panel.staticTextCurrentGonio.SetLabel('') #(gon.name)
            self.panel.currentControl = self.current_gon_copy.edit_traits(parent=self.panel, kind='subpanel').control
            self.panel.boxSizerAll.Insert(2, self.panel.currentControl, 0, flag=wx.EXPAND | wx.SHRINK)

        self.panel.boxSizerAll.Layout()

    #------------------------------------------------------------------
    def update_current(self):
        # Start by making a full copy of the current goniometer
        gon = copy.deepcopy(model.instrument.inst.goniometer)
        self.current_gon_copy = gon
        self.show_current_gon_copy()

    #------------------------------------------------------------------
    def update_selection(self):
        gon = self.selected
        if gon is None:
            self.panel.staticTextDesc.SetLabel(" ")
            self.panel.currentControl = None
        else:
#            self.panel.staticTextDesc.SetLabel(gon.description + "\n\n" + gon.get_angles_description())
            self.panel.staticTextDesc.SetLabel(gon.description)
        #Wrapping the text is the only solution I found to making the layout good.
        # self.panel.staticTextDesc.Wrap(self.panel.GetSize()[0]-60)
        self.panel.boxSizerAll.Layout()

    #------------------------------------------------------------------
    def select_current(self):
        """Makes the current goniometer the selected one too."""
        pass


    #------------------------------------------------------------------
    def on_goniometer_choice(self, event):
        """When the choice of goniometer changes"""
        index = self.panel.choiceGonio.GetSelection()
        if index < 0 or index >= len(model.goniometer.goniometers):
            self.selected = None
        else:
            #Select this one
            self.selected = model.goniometer.goniometers[index]
            
        #Update the view
        self.update_selection()

        if not event is None:
            event.Skip()

    #------------------------------------------------------------------
    def edit_angles(self, event):
        """Open dialog to change the angles"""
        # The dialog will change the object in place, unless cancelled
        dialog_goniometer_angles.show_dialog(self.panel, self.current_gon_copy)
        # Refresh the view, in case something was modified
        self.panel.currentControl.Refresh()


    #------------------------------------------------------------------
    def apply_changes(self, event):
        """Changes settings on current goniometer."""
        self.change_goniometer(self.current_gon_copy)
        event.Skip()

    #------------------------------------------------------------------
    def change_goniometer(self, new_gonio):
        """Change to a new/modified goniometer"""
        old_gonio = model.instrument.inst.goniometer
        if not (new_gonio is None):
            if (new_gonio == old_gonio):
                #It is the same
                wx.MessageDialog(self.panel, "Your experiment is already using this same goniometer.", "Same Goniometer", wx.OK).ShowModal()
            else:
                #Something changed
                different_angles = len(new_gonio.angles) != len(old_gonio.angles)
                if different_angles and len(model.instrument.inst.positions)>0:
                    #Prompt the user
                    res = wx.MessageDialog(self.panel, "The new goniometer does not have the same angles listed as the old one. This means that all current sample orientations saved will have to be deleted. Are you sure?", "Changing Goniometer", wx.YES_NO | wx.NO_DEFAULT).ShowModal()
                    if res == wx.NO:
                        return
                #Apply the change
                model.instrument.inst.set_goniometer(new_gonio, different_angles)
                #Send a message to do other updates
                model.messages.send_message(model.messages.MSG_GONIOMETER_CHANGED, "")
                #Show the current gonio
                self.update_current()

    #------------------------------------------------------------------
    def switch_goniometer(self, event):
        """Select the goniometer shown."""
        self.change_goniometer(self.selected)
        if not event is None:
            event.Skip()



#====================================================================================
#====================================================================================
class PanelGoniometer(wx.Panel):
    """Goniometer selection GUI."""
    def _init_coll_boxSizerall_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.boxSizerSelected, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonEditAngles, 0, border=24, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonApplyChanges, 0, border=24, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(wx.StaticLine(self), 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextTitle, 0, border=4, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.choiceGonio, 0, border=8,
              flag=wx.RIGHT | wx.LEFT | wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=4, flag=wx.LEFT)
        parent.Add(self.staticTextDescLabel, 0, border=4, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=4, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextDesc, 0, border=24,
              flag=wx.RIGHT | wx.LEFT | wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonSwitchGoniometer, 0, border=24, flag=wx.LEFT)
        parent.Add(wx.Size(8, 8), border=4, flag=0)

    def _init_coll_boxSizerSelected_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticText1, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextCurrentGonio, 0, border=0, flag=0)

    def _init_sizers(self):
        # generated method, don't edit
        self.boxSizerAll = wx.BoxSizer(orient=wx.VERTICAL)

        self.boxSizerSelected = wx.BoxSizer(orient=wx.HORIZONTAL)

        self._init_coll_boxSizerall_Items(self.boxSizerAll)
        self._init_coll_boxSizerSelected_Items(self.boxSizerSelected)

        self.SetSizer(self.boxSizerAll)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Panel.__init__(self, id=wxID_PANELGONIOMETER,
              name='PanelGoniometer', parent=prnt, pos=wx.Point(637, 307), style=wx.TAB_TRAVERSAL)
        self.SetClientSize(wx.Size(626, 618))

        self.staticTextTitle = wx.StaticText(id=wxID_PANELGONIOMETERSTATICTEXTTITLE,
              label='Available Goniometers:', name='staticTextTitle',
              parent=self, pos=wx.Point(0, 8), style=0)

        self.choiceGonio = wx.Choice(choices=model.goniometer.get_goniometers_names(),
              id=wxID_PANELGONIOMETERCHOICEGONIO, name='choiceGonio',
              parent=self, pos=wx.Point(8, 33), style=0)
        self.choiceGonio.Bind(wx.EVT_CHOICE, self.controller.on_goniometer_choice)

        self.staticText1 = wx.StaticText(id=wxID_PANELGONIOMETERSTATICTEXT1,
              label='Current Goniometer:', name='staticText1', parent=self,
              pos=wx.Point(8, 70), style=0)
        self.staticText1.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False, 'Sans'))

        self.staticTextDescLabel = wx.StaticText(id=wxID_PANELGONIOMETERSTATICTEXTDESCLABEL,
              label='Description:', name='staticTextDescLabel', parent=self,
              pos=wx.Point(0, 95), style=0)

        self.staticTextCurrentGonio = wx.StaticText(id=wxID_PANELGONIOMETERstaticTextCurrentGonio,
              label='name of selected', name='staticTextCurrentGonio',
              parent=self, style=0)
        self.staticTextCurrentGonio.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False, 'Sans'))

        self.staticTextDesc = wx.StaticText(id=wxID_PANELGONIOMETERSTATICTEXTDESC,
              label='... ... text ... ...', name='staticTextDesc',
              parent=self, 
              style=0)

        self.buttonApplyChanges = wx.Button(label='  Apply Changes to Goniometer...  ', parent=self,
              pos=wx.Point(4, 734),  style=0)
        self.buttonApplyChanges.SetToolTip('Applies any changes made to the current goniometer. ')
        self.buttonApplyChanges.Bind(wx.EVT_BUTTON, self.controller.apply_changes)

        self.buttonEditAngles = wx.Button(label='  Edit Angles (advanced)...  ', parent=self,
              pos=wx.Point(4, 734),  style=0)
        self.buttonEditAngles.SetToolTip('Change the details on the goniometer angles.')
        self.buttonEditAngles.Bind(wx.EVT_BUTTON, self.controller.edit_angles)

        self.buttonSwitchGoniometer = wx.Button(label='  Switch to this goniometer  ', parent=self,
              pos=wx.Point(4, 734), style=0)
        self.buttonSwitchGoniometer.SetToolTip('Select the goniometer shown for this experiment. ')
        self.buttonSwitchGoniometer.Bind(wx.EVT_BUTTON, self.controller.switch_goniometer)

        
    def __init__(self, parent):
        self.controller = PanelGoniometerController(self)
        
        self._init_ctrls(parent)
        self._init_sizers()
        self.currentControl = None

        self.controller.update_current()
        self.controller.update_selection()
        self.controller.select_current()

    def Refresh(self):
        self.controller.update_current()
        self.controller.update_selection()
        self.controller.select_current()


    def needs_apply(self):
        """Return True if the panel needs to be applied, because a setting changed."""
        return (self.controller.current_gon_copy != model.instrument.inst.goniometer)






#====================================================================================
if __name__ == "__main__":
    model.instrument.inst = model.instrument.Instrument()
    model.goniometer.initialize_goniometers()
    (app, pnl) = gui_utils.test_my_gui(PanelGoniometer)
    pnl.SetClientSize(wx.Size(1200,1200))
    app.MainLoop()
