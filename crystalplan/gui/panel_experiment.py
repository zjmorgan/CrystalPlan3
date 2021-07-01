#Boa:FramePanel:PanelExperiment
"""PanelExperiment: panel showing a list of sample orientations and the
settings to use (runtime) during the experiment."""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- General Imports ---
import wx
import wx.grid

#--- GUI Imports ---
from crystalplan.gui import gui_utils
from crystalplan.gui import display_thread
from crystalplan.gui import frame_optimizer

#--- Model Imports ---
from crystalplan import model

#--- Traits Imports ---
from traits.api import HasTraits,Int,Float,Str,String,Property,Bool, List, Tuple, Array, Enum
from traitsui.api import View,Item,Label,Heading, Spring, Handler, Group
from traitsui.menu import OKButton, CancelButton
from traitsui.editors import EnumEditor


[wxID_PANELEXPERIMENT, wxID_PANELEXPERIMENTBUTTONDELETEALL, 
 wxID_PANELEXPERIMENTBUTTONDELETEHIGHLIGHTED, 
 wxID_PANELEXPERIMENTBUTTONDELETEUNUSED, 
 wxID_PANELEXPERIMENTBUTTONREFRESHLIST, wxID_PANELEXPERIMENTBUTTONSAVETOCSV, 
 wxID_PANELEXPERIMENTcheckUseAll,
 wxID_PANELEXPERIMENTCHECKSELECTHIGHLIGHTED, wxID_PANELEXPERIMENTGRIDEXP, 
 wxID_PANELEXPERIMENTSTATICTEXTESTIMATEDTIME, 
 wxID_PANELEXPERIMENTSTATICTEXTHELP, 
] = [wx.NewId() for _init_ctrls in range(11)]


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
class ExperimentGridController():
    """View/Controller for the sample orientation grid."""
    panel = None 

    #----------------------------------------------------------------------------------------
    def __init__(self, panel):
        """Constructor."""
        self.panel = panel
        self.inside_set_checkUseAll = False
        #Make sure the initial draw is good
        self.panel.gridExp.CreateGrid(1, 1)
        self.grid_setup()
        #Subscribe to messages about the list of positions
        model.messages.subscribe(self.update_grid, model.messages.MSG_POSITION_LIST_CHANGED)
        model.messages.subscribe(self.update_selection, model.messages.MSG_POSITION_SELECTION_CHANGED)
        model.messages.subscribe(self.on_goniometer_changed, model.messages.MSG_GONIOMETER_CHANGED)
        model.messages.subscribe(self.update_estimated_time, model.messages.MSG_EXPERIMENT_QSPACE_CHANGED)
        #Fill with current data
        self.update_grid()
        #Show the selected stuff
        self.update_selection()

    #-------------------------------------------------------------------------------
    def on_goniometer_changed(self, *args):
        """Called when the goniometer used changes."""
        #Setup needs to be redone
        self.grid_setup()
        #Fill with current data
        self.update_grid()
        #Show the selected stuff
        self.update_selection()


    #----------------------------------------------------------------------------------------
    def grid_setup(self):
        """Perform the initial setup and layout of the grid."""
        # @type grid wx.grid.Grid
        grid = self.panel.gridExp
        #General settings
        #grid.SetSelectionMode(wx.grid.Grid.wxGridSelectRows)
        #Label width/height
        grid.SetColLabelSize(40)
        grid.SetRowLabelSize(40)
        
        #Find that the grid should be
        num_angles = len(model.instrument.inst.angles)
        num_cols = 4 + num_angles
        if grid.GetNumberCols() > num_cols:
            grid.DeleteCols(0, grid.GetNumberCols() -num_cols)
        if grid.GetNumberCols() < num_cols:
            grid.AppendCols(num_cols - grid.GetNumberCols())

        #The column headers
        grid.SetColLabelValue(0, "Use?")
        grid.SetColSize(0, 50)
        #Column # of the criterion
        self.criterion_col = num_angles+1
        grid.SetColLabelValue(self.criterion_col, "Stopping\nCriterion")
        grid.SetColSize(self.criterion_col, 180)
        grid.SetColLabelValue(self.criterion_col+1, "Criterion\nValue")
        grid.SetColSize(self.criterion_col+1, 100)
        grid.SetColLabelValue(self.criterion_col+2, "Comment")
        grid.SetColSize(self.criterion_col+2, 120)
        for (i, anginfo) in enumerate(model.instrument.inst.angles):
            grid.SetColLabelValue(i+1, anginfo.name + "\n(" + anginfo.friendly_units + ")")
            grid.SetColSize(i+1, 100)
                    
    #------------------------------------
    def update_grid(self, *args):
        """Fill the grid rows with data, and set the right editors."""
        # @type grid wx.grid.Grid
        grid = self.panel.gridExp

        #Adjust number of rows
        num_rows = len(model.instrument.inst.positions)
        if grid.GetNumberRows() > num_rows:
            grid.DeleteRows(0, grid.GetNumberRows()-num_rows)
        else:
            old_num_rows = grid.GetNumberRows()
            grid.AppendRows(num_rows-grid.GetNumberRows())
            #Set the editors for the new rows
            choices = model.experiment.get_stopping_criteria_names()
            for row in range(old_num_rows, num_rows):
                grid.SetCellEditor(row, self.criterion_col, wx.grid.GridCellChoiceEditor(choices))


        #Font for angles
        angle_font = wx.Font(10, 76, wx.NORMAL, wx.NORMAL, False, 'Monospace')
        for (i, poscov) in enumerate(model.instrument.inst.positions):
            row = i
            #The checkbox
            grid.SetCellAlignment(row, 0, wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
            grid.SetReadOnly(row, 0, True) #Do set it read-only
            #The angles
            for (j, angleinfo) in enumerate(model.instrument.inst.angles):
                x = poscov.angles[j]
                col = j+1
                grid.SetCellValue(row, col, "%8.2f" % angleinfo.internal_to_friendly(x))
                grid.SetReadOnly(row, col, True) #Do set it read-only
                grid.SetCellAlignment(row, col, wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
                grid.SetCellFont(row, col, angle_font)
            #The criterion
            grid.SetCellValue(row, self.criterion_col, model.experiment.get_stopping_criterion_friendly_name(poscov.criterion))
            grid.SetCellValue(row, self.criterion_col+1, str(poscov.criterion_value))
            #Comment string
            grid.SetCellValue(row, self.criterion_col+2, str(poscov.comment))

        self.update_selection()

#    #----------------------------------------------------------------------------------------
#    def fix_editors(self):
#        """Fix the cell editors for all columns and all rows.
#        Call when loading an experiment, to ensure the column editors are ok."""
#        # @type grid wx.grid.Grid
#        grid = self.panel.gridExp
#
#        for row in xrange(0, grid.GetNumberRows()):
#            grid.SetCellEditor(row, self.criterion_col, wx.grid.GridCellChoiceEditor(choices))


    #----------------------------------------------------------------------------------------
    def update_selection(self, message=None):
        """Updates the GUI to reflect all the selected positions in the latest parameters.
        If message is set, this is the handler for an external change in selection.
        The message.data dictionary is used instead of latestparams.
        """
        #Re-check the previously checked items.
        if message is None:
            pos_dict = display_thread.get_positions_dict()
        else:
            pos_dict = message.data

        grid = self.panel.gridExp

        all_selected = True
        for i in range( grid.GetNumberRows() ):
            #Get the position from the instruments' list.
            if i < len(model.instrument.inst.positions):
                pos = model.instrument.inst.positions[i]
                #Default to False
                this_one_is_selected = pos_dict.get(id(pos), False)
                #Show a space for False.
                val = [" ", "X"][this_one_is_selected]
                #Count if all are selected
                all_selected = all_selected and this_one_is_selected
            else:
                val = "?"
                all_selected = False

            #Check it if you find it, and it's true.
            grid.SetCellValue(i, 0, val )
            grid.SetCellAlignment(i, 0, wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
            
        #If the selection changes, the estimated time will change too
        self.update_estimated_time()

        #And the "use all" checkbox
        self.inside_set_checkUseAll = True
        self.panel.checkUseAll.SetValue(all_selected)
        self.inside_set_checkUseAll = False

    #----------------------------------------------------------------------------------------
    def update_estimated_time(self, *args):
        """Display the estimated experiment time."""
        s = model.experiment.exp.estimated_time_string()
        self.panel.staticTextEstimatedTime.SetLabel("Estimated run time: " + s)
        self.panel.boxSizerAll.Layout()
        self.panel.Layout()

    #----------------------------------------------------------------------------------------
    def cell_changed(self, event):
        """Called when a cell is changed by the user."""
        # @type event wx.grid.GridEvent
        #Find the positionCoverage object
        row = event.GetRow()
        poscov = model.instrument.inst.get_position_num(row)
        if poscov is None:
            return #Can't do anything is something is screwy here

        #What string was typed in?
        col = event.GetCol()
        cell_str = self.panel.gridExp.GetCellValue(row, col)

        if col == 0:
            #Clicked use/don't use
            value = (cell_str == "X")
#            print "changed use box to ", cell_str, value
            #Select or de-select these
            display_thread.select_additional_position_coverage(poscov, update_gui=False, select_items=value)
        elif col == self.criterion_col:
            #Changed criterion
            poscov.criterion = model.experiment.get_stopping_criterion_from_friendly_name(cell_str)
            #Need to update the time estimate
            self.update_estimated_time()
        elif col == self.criterion_col+1:
            #Criterion value
            try:
                poscov.criterion_value = float(cell_str)
            except ValueError:
                #Invalid input to the string, revert display to show the original value
                self.panel.gridExp.SetCellValue(row, col, str(poscov.criterion_value))
            #Need to update the time estimate
            self.update_estimated_time()
        elif col == self.criterion_col+2:
            #Comment
            poscov.comment = cell_str
        else:
            raise NotImplementedError("You should not be able to edit this cell, as it is read-only!")
                


    #----------------------------------------------------------------------------------------
    def cell_double_click(self, event):
        """Called when a cell is double-clicked by the user."""
        # @type event wx.grid.GridEvent
        #Find the positionCoverage object
        row = event.GetRow()
        poscov = model.instrument.inst.get_position_num(row)
        if poscov is None:
            return #Can't do anything is something is screwy here

        #Where did we click?
        col = event.GetCol()

        if col == 0:
            #Find what it is now
            was_selected = display_thread.is_position_selected(poscov)
            #Toggle the selection state
            display_thread.select_additional_position_coverage(poscov, update_gui=True, select_items=(not was_selected))

    #----------------------------------------------------------------------------------------
    def label_dclick(self, event):
        """Called when double-clicked a label"""
        row = event.GetRow()
        col = event.GetCol()
        if row == -1:
            #Clicked on the header
            #Index in the list of angles that was clicked
            angle_num = col - 1
            model.instrument.inst.sort_positions_by(angle_num)
            #Update
            self.update_grid()


            


    #----------------------------------------------------------------------------------------
    def select_all(self, value):
        """Select or deselect all items in the list."""
        if not self.inside_set_checkUseAll:
            display_thread.select_additional_position_coverage(model.instrument.inst.positions, update_gui=True, select_items=value)

    #----------------------------------------------------------------------------------------
    def set_criterion(self, selection, criterion, value):
        """Set the stopping criteria for the selected rows.
        Parameters:
            selection: list of rows.
            criterion: string (friendly) name of the criterion
            value: float, value to stop at.
        """
        for row in selection:
            model.instrument.inst.positions[row].criterion = model.experiment.get_stopping_criterion_from_friendly_name(criterion)
            model.instrument.inst.positions[row].criterion_value = value
        self.update_grid()



    #----------------------------------------------------------------------------------------
    def select_several(self, row_list, value):
        """Select or deselect several items in the list.

        Parameter:
            row_list: list of row numbers to delete.
        """
        poscov_list = [model.instrument.inst.positions[x] for x in row_list if (x>=0) and (x<len(model.instrument.inst.positions))]
        display_thread.select_additional_position_coverage(poscov_list, update_gui=True, select_items=value)
        #Make sure the GUI updates
        self.update_selection()


    #----------------------------------------------------------------------------------------
    def delete_all(self):
        """Deletes all entries in the position list."""
        #This deletes everything in the list
        del model.instrument.inst.positions[:]
        #Make sure to clear the parameters too, by giving it an empty dict() object.
        display_thread.clear_positions_selected()
        #Update the display.
        self.update_grid()

    #----------------------------------------------------------------------------------------
    def delete_several(self, row_list):
        """Deletes several entries in the position list.

        Parameter:
            row_list: list of row numbers to delete.
        """
        #Get the current selection dictionary
        poscov_dict = display_thread.get_positions_dict().copy()
        #Delete entries, starting from the end
        row_list.sort()
        row_list.reverse()
        for index in row_list:
            #Remove from the selection list too
            poscov = model.instrument.inst.positions[index]
            if id(poscov) in poscov_dict:
                del poscov_dict[id(poscov)]
            #And from the data
            del model.instrument.inst.positions[index]

        #Remove the extra entries from the list
        display_thread.select_position_coverage(poscov_dict, update_gui=False)

        #Update the display.
        self.update_grid()


#========================================================================================
class StoppingCriterionParams(HasTraits):
    """Small class to make a quick GUI for the stopping parameters."""
    criterion_value = Float(60.0, desc="the value corresponding to the specified criterion.")
    criterion_list = ["1"]
    stopping_criterion = "1"
    
    def get_view(self):
        return View(
            Item('stopping_criterion', editor=EnumEditor(name="criterion_list")),
            Item('criterion_value'), buttons=[OKButton, CancelButton] )

    def __init__(self):
        self.criterion_list = model.experiment.get_stopping_criteria_names()
        self.add_trait("stopping_criterion", Enum( self.criterion_list ) )
        self.stopping_criterion = self.criterion_list[0]


#========================================================================================
class PanelExperiment(wx.Panel):
    def _init_coll_boxSizerDelete_Items(self, parent):
        # generated method, don't edit

        parent.Add(self.buttonDeleteAll, 0, border=4,
              flag=wx.LEFT | wx.RIGHT)
        parent.Add(self.buttonDeleteHighlighted, 0, border=4,
              flag=wx.LEFT | wx.RIGHT)
        parent.Add(self.buttonDeleteUnused, 0, border=4,
              flag=wx.LEFT | wx.RIGHT)
        parent.AddStretchSpacer(1)
        parent.Add(self.buttonRefreshList, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)

    def _init_coll_boxSizerEstimatedTime_Items(self, parent):
        # generated method, don't edit
        pass
        #parent.AddWindow(self.staticTextEstimatedTime, 0, border=12, flag=wx.EXPAND  | wx.LEFT | wx.RIGHT)

    def _init_coll_boxSizerSelect_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.checkUseAll, 0, border=0,
              flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextHighlighted, 0, border=0,
              flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonUseHighlighted, 0, border=0,
              flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonDontUseHighlighted, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonChangeStopping, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)

    def _init_coll_boxSizerSave_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonSaveToCSV, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.AddStretchSpacer(1)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.buttonOptimizer, 0, border=0, flag=0)
        parent.Add(wx.Size(8, 8), border=0, flag=0)

    def _init_coll_boxSizerAll_Items(self, parent):
        # generated method, don't edit

        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextHelp, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.boxSizerSelect, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.gridExp, 1, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.boxSizerDelete, 0, border=0,
              flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.staticTextEstimatedTime, 0, border=12, flag=wx.EXPAND  | wx.LEFT | wx.RIGHT)
        #parent.Add(self.boxSizerEstimatedTime, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)
        parent.Add(self.boxSizerSave, 0, border=0, flag=wx.EXPAND)
        parent.Add(wx.Size(8, 8), border=0, flag=0)

    def _init_sizers(self):
        # generated method, don't edit
        self.boxSizerAll = wx.BoxSizer(orient=wx.VERTICAL)

        self.boxSizerSelect = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.boxSizerDelete = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.boxSizerEstimatedTime = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.boxSizerSave = wx.BoxSizer(orient=wx.HORIZONTAL)

        self._init_coll_boxSizerAll_Items(self.boxSizerAll)
        self._init_coll_boxSizerSelect_Items(self.boxSizerSelect)
        self._init_coll_boxSizerDelete_Items(self.boxSizerDelete)
        self._init_coll_boxSizerEstimatedTime_Items(self.boxSizerEstimatedTime)
        self._init_coll_boxSizerSave_Items(self.boxSizerSave)

        self.SetSizer(self.boxSizerAll)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Panel.__init__(self, id=wxID_PANELEXPERIMENT,
              name='PanelExperiment', parent=prnt, pos=wx.Point(633, 252),
              size=wx.Size(600, 849), style=wx.TAB_TRAVERSAL)
        self.SetClientSize(wx.Size(600, 849))
        self.SetAutoLayout(True)

        self.gridExp = wx.grid.Grid(id=wxID_PANELEXPERIMENTGRIDEXP,
              name='gridExp', parent=self, pos=wx.Point(0, 70),
              size=wx.Size(1, 1), style=0)
        self.gridExp.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnGridExpGridCellLeftClick)
        self.gridExp.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnGridExpGridCellLeftDoubleClick)
        self.gridExp.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridExpGridCellRightClick)
        self.gridExp.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnGridExpGridCellChange)
        self.gridExp.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnGridExpGridEditorCreated)
        self.gridExp.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnGridExpGridLabelLeftClick)
        self.gridExp.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.OnGridExpGridLabelLeftDClick)
        self.gridExp.SetToolTip("Double-click on an angle column header to sort the list by that angle.")

        self.staticTextHelp = wx.StaticText(id=wxID_PANELEXPERIMENTSTATICTEXTHELP,
              label='Select the sample orientations you wish to use in the experiment, and the criterion for data acquisition at each orientation.',
              name='staticTextHelp', parent=self, pos=wx.Point(0, 8),
              style=0)
        self.staticTextHelp.SetAutoLayout(True)
        if gui_utils.is_mac():
            self.staticTextHelp.Wrap(self.GetSize()[0]-50)

        self.staticTextEstimatedTime = wx.StaticText(id=wxID_PANELEXPERIMENTSTATICTEXTESTIMATEDTIME,
              label='Estimated Time:', name='staticTextEstimatedTime',
              parent=self, size=wx.Size(100, 35), style=0) #wx.ST_NO_AUTORESIZE)
        self.staticTextEstimatedTime.SetAutoLayout(True)

        self.checkUseAll = wx.CheckBox(id=wxID_PANELEXPERIMENTcheckUseAll,
              label='Use All', name='checkUseAll', parent=self,
              pos=wx.Point(8, 36), size=wx.Size(95, 22), style=0)
        self.checkUseAll.SetValue(True)
        self.checkUseAll.Bind(wx.EVT_CHECKBOX, self.OncheckUseAllCheckbox,
              id=wxID_PANELEXPERIMENTcheckUseAll)
        self.checkUseAll.SetToolTip("Check the box to use all the sample orientations in the list; uncheck it to clear the list.")

        self.staticTextHighlighted = wx.StaticText(label='Highlighted Rows:',
              name='staticTextHighlighted', parent=self, pos=wx.Point(0, 8),
              style=0)
        self.staticTextHighlighted.SetAutoLayout(True)

        self.buttonUseHighlighted = wx.Button(label='Use', name='buttonUseHighlighted', parent=self,
              pos=wx.Point(4, 734), size=wx.Size(65, 29), style=0)
        self.buttonUseHighlighted.SetToolTip('Select to use all the highlighted rows in the grid below.')
        self.buttonUseHighlighted.Bind(wx.EVT_BUTTON, self.OnButtonUseHighlighted)

        self.buttonDontUseHighlighted = wx.Button(label=" Don't Use ", name='buttonDontUseHighlighted', parent=self,
              pos=wx.Point(4, 734), size=wx.Size(95, 29), style=0)
        self.buttonDontUseHighlighted.SetToolTip('Select not to use all the highlighted rows in the grid below.')
        self.buttonDontUseHighlighted.Bind(wx.EVT_BUTTON, self.OnButtonDontUseHighlighted)

        self.buttonDeleteAll = wx.Button(id=wxID_PANELEXPERIMENTBUTTONDELETEALL,
              label='  Delete All  ', name='buttonDeleteAll', parent=self,
              pos=wx.Point(4, 734), style=0)
        self.buttonDeleteAll.SetToolTip('Delete all the orientations in the list.')
        self.buttonDeleteAll.Bind(wx.EVT_BUTTON, self.OnButtonDeleteAllButton,
              id=wxID_PANELEXPERIMENTBUTTONDELETEALL)

        self.buttonDeleteHighlighted = wx.Button(id=wxID_PANELEXPERIMENTBUTTONDELETEHIGHLIGHTED,
              label='  Delete Highlighted  ', name='buttonDeleteHighlighted',
              parent=self, pos=wx.Point(97, 734), style=0)
        self.buttonDeleteHighlighted.SetToolTip('Delete the orientations in rows above that are highlighted.')
        self.buttonDeleteHighlighted.Bind(wx.EVT_BUTTON,
              self.OnButtonDeleteHighlightedButton,
              id=wxID_PANELEXPERIMENTBUTTONDELETEHIGHLIGHTED)

        self.buttonDeleteUnused = wx.Button(id=wxID_PANELEXPERIMENTBUTTONDELETEUNUSED,
              label='  Delete Unused  ', name='buttonDeleteUnused', parent=self,
              pos=wx.Point(249, 734), style=0)
        self.buttonDeleteUnused.SetToolTip('Delete all the orientations in the list that are unused (unchecked).')
        self.buttonDeleteUnused.Bind(wx.EVT_BUTTON,
              self.OnButtonDeleteUnusedButton,
              id=wxID_PANELEXPERIMENTBUTTONDELETEUNUSED)

        self.buttonSaveToCSV = wx.Button(id=wxID_PANELEXPERIMENTBUTTONSAVETOCSV,
              label='  Save to .CSV file  ', name='buttonSaveToCSV', parent=self,
              pos=wx.Point(0, 804), style=0)
        self.buttonSaveToCSV.Bind(wx.EVT_BUTTON, self.OnButtonSaveToCSVButton,
              id=wxID_PANELEXPERIMENTBUTTONSAVETOCSV)
        self.buttonSaveToCSV.SetToolTip("Choose a path to save the list of sample orientations to a .CSV file compatible with PyDas (SNS data acquisition system python scripting).")

        self.buttonOptimizer = wx.Button(id=wx.NewId(), label='  Automatic Coverage Optimizer...  ', name='buttonOptimizer', parent=self,
              pos=wx.Point(0, 804), style=0)
        self.buttonOptimizer.Bind(wx.EVT_BUTTON, self.OnButtonOptimizer)
        self.buttonOptimizer.SetToolTip("Open the Experiment Plan Automatic Optimizer window.")

        self.buttonRefreshList = wx.Button(id=wxID_PANELEXPERIMENTBUTTONREFRESHLIST,
              label=' Refresh List ', name='buttonRefreshList', parent=self,
              pos=wx.Point(240, 33), style=0)
        self.buttonRefreshList.Bind(wx.EVT_BUTTON,
              self.OnButtonRefreshListButton,
              id=wxID_PANELEXPERIMENTBUTTONREFRESHLIST)

        self.buttonChangeStopping = wx.Button(id=wx.NewId(),
              label='  Change Stopping Criteria  ', name='buttonChangeStopping', parent=self,
              pos=wx.Point(240, 33), style=0)
        self.buttonChangeStopping.Bind(wx.EVT_BUTTON, self.OnButtonChangeStopping)
        self.buttonChangeStopping.SetToolTip("Change the stopping criteria and value for all selected rows.")
              
        self._init_sizers()

    def __init__(self, parent):
        #Some pre-controls initialization
        self.prev_rowcol = [None, None]

        #Do the controls
        self._init_ctrls(parent)

        #Set the controller
        self.controller = ExperimentGridController(self)
        
    def Refresh(self):
        #Delete all rows and refresh
        self.gridExp.DeleteRows(0, self.gridExp.GetNumberRows())
        self.controller.grid_setup()
        self.controller.update_grid()

    def OnGridExpGridCellLeftClick(self, event):
        event.Skip()

    def OnGridExpGridCellLeftDoubleClick(self, event):
        self.controller.cell_double_click(event)
        event.Skip()

    def OnGridExpGridCellRightClick(self, event):
        event.Skip()

    def OnGridExpGridCellChange(self, event):
        self.controller.cell_changed(event)
        event.Skip()

    def OncheckUseAllCheckbox(self, event):
        #Call this after checking it
        wx.CallAfter(self.controller.select_all, self.checkUseAll.GetValue() )
        event.Skip()

    def get_selected_rows(self):
        """Return a list of rows that have been selected, combining
        block and row selections."""
        grid = self.gridExp
        #List of rows
        selection = self.gridExp.GetSelectedRows()
        if len(grid.GetSelectionBlockTopLeft()) > 0:
            #If a block is selected from column 0 to last col (any rows)
            if grid.GetSelectionBlockTopLeft()[0][1] == 0  \
                and grid.GetSelectionBlockBottomRight()[0][1] == grid.GetNumberCols()-1:
                    #Add a list of the selected rows (inclusively)
                    selection += list(range(grid.GetSelectionBlockTopLeft()[0][0], grid.GetSelectionBlockBottomRight()[0][0]+1))
        return selection

    def OnButtonUseHighlighted(self, event):
        self.controller.select_several(self.get_selected_rows(), True)
        event.Skip()

    def OnButtonDontUseHighlighted(self, event):
        self.controller.select_several(self.get_selected_rows(), False)
        event.Skip()

    def OnButtonDeleteAllButton(self, event):
        ret = wx.MessageBox("Do you really want to delete all the entries in the experiment sample orientation list?", "Delete All?", style=wx.YES_NO | wx.NO_DEFAULT)
        if ret == wx.YES:
            self.controller.delete_all()
        event.Skip()

    def OnButtonDeleteHighlightedButton(self, event):
        self.ask_to_delete_several(self.get_selected_rows(), "no rows are highlighted.")
        event.Skip()

    def OnButtonDeleteUnusedButton(self, event):
        unused_list = []
        for (i, poscov) in enumerate(model.instrument.inst.positions):
            if not display_thread.is_position_selected(poscov):
                unused_list.append(i)
        self.ask_to_delete_several(unused_list, "all sample orientations in the list are checked as being used.")
        event.Skip()

    def ask_to_delete_several(self, row_list, nothing_message):
        if len(row_list) <= 0:
            wx.MessageBox("Nothing to delete - %s" % nothing_message, "Delete Sample Orientations?", style=wx.OK)
        else:
            ret = wx.MessageBox("Do you really want to delete %d entries in the experiment sample orientation list?" % len(row_list), "Delete Entries?", style=wx.YES_NO | wx.NO_DEFAULT)
            if ret == wx.YES:
                self.controller.delete_several(row_list)
                #Selected rows become screwy after deletion
                self.gridExp.ClearSelection()

    def OnButtonChangeStopping(self, event):
        selection = self.get_selected_rows()
        if len(selection) <= 0:
            wx.MessageBox("No rows are highlighted! Highlight some before clicking.", "No rows highlighted.", style=wx.OK | wx.ICON_EXCLAMATION)
        else:
            #Prompt for the stopping criterion.
            crit = StoppingCriterionParams()
            poscov = model.instrument.inst.positions[ selection[0] ] #@type poscov PositionCoverage
            #Default value
            if not poscov is None:
                crit.stopping_criterion = model.experiment.get_stopping_criterion_friendly_name(poscov.criterion)
                crit.criterion_value = poscov.criterion_value
                
            res = crit.configure_traits(kind="modal", view=crit.get_view())
            if res:
                #Clicked ok.
                self.controller.set_criterion(selection, crit.stopping_criterion, crit.criterion_value)
        event.Skip()


    def OnButtonSaveToCSVButton(self, event):
        gui_utils.dialog_to_save_experiment_to_CSV(self)
        event.Skip()

    def OnButtonOptimizer(self, event):
        frm = frame_optimizer.get_instance(parent=self)
        frm.Show()
        frm.Raise()
        event.Skip()

    def OnGridExpGridEditorCreated(self, event):
        event.Skip()

    def OnGridExpGridLabelLeftClick(self, event):
        event.Skip()

    def OnGridExpGridLabelLeftDClick(self, event):
        self.controller.label_dclick(event)
        event.Skip()

    def OnButtonRefreshListButton(self, event):
        self.controller.update_grid()
        event.Skip()





if __name__ == "__main__":
    #Ok, create the instrument
    model.instrument.inst = model.instrument.Instrument("model/TOPAZ_geom_all_2011.csv")
    model.instrument.inst.make_qspace()
    #Initialize the instrument and experiment
    model.experiment.exp = model.experiment.Experiment(model.instrument.inst)
#    import numpy as np
#    for i in np.deg2rad(np.arange(0, 36, 12)):
#        model.instrument.inst.simulate_position(list([i,i,i]))
#    pd = dict()
#    for pos in model.instrument.inst.positions:
#        pd[ id(pos) ] = True
#    display_thread.NextParams[model.experiment.PARAM_POSITIONS] = model.experiment.ParamPositions(pd)
    from . import gui_utils
    (app, pnl) = gui_utils.test_my_gui(PanelExperiment)
    app.frame.SetClientSize(wx.Size(700,500))
    app.MainLoop()
