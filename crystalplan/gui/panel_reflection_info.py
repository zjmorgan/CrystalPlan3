#Boa:FramePanel:PanelReflectionInfo
"""PanelReflectionInfo: panel showing info on a single reflection,
e.g. how many times it was measured, etc."""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- General Imports ---
import wx
import numpy as np

#--- GUI Imports ---
from crystalplan.gui.panel_reflection_measurement import PanelReflectionMeasurement
from crystalplan.gui import gui_utils
from crystalplan.gui import reflection_placer

#--- Model Imports ---
from crystalplan import model
from crystalplan.model.reflections import ReflectionMeasurement, Reflection, ReflectionRealMeasurement

#================================================================================
#================================================================================
#================================================================================
[wxID_PANELREFLECTIONINFO, wxID_PANELREFLECTIONINFOSCROLLEDWINDOWMEASUREMENTS, 
 wxID_PANELREFLECTIONINFOSTATICTEXTDLABEL, 
 wxID_PANELREFLECTIONINFOSTATICTEXTHKLLABEL, 
 wxID_PANELREFLECTIONINFOSTATICTEXTQLABEL, 
 wxID_PANELREFLECTIONINFOSTATICTEXTTIMESMEASURED, 
 wxID_PANELREFLECTIONINFOTEXTCTRLDSPACING, wxID_PANELREFLECTIONINFOTEXTCTRLH, 
 wxID_PANELREFLECTIONINFOTEXTCTRLK, wxID_PANELREFLECTIONINFOTEXTCTRLL, 
 wxID_PANELREFLECTIONINFOTEXTCTRLQ, 
] = [wx.NewId() for _init_ctrls in range(11)]

class PanelReflectionInfo(wx.Panel):
    def _init_coll_flexGridSizerTop_Items(self, parent):
        # generated method, don't edit

        parent.Add(self.staticTextHKLLabel, 0, border=0,
              flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(self.gridSizerHKL, 1, border=0, flag=wx.EXPAND)
        parent.Add(self.staticTextQLabel, 0, border=0,
              flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(self.textCtrlQ, 0, border=0, flag=wx.EXPAND)
        parent.Add(self.staticTextDlabel, 0, border=0,
              flag=wx.ALIGN_CENTER_VERTICAL)
        parent.Add(self.textCtrlDspacing, 0, border=0, flag=wx.EXPAND)

        parent.Add(self.staticDivergenceLabel, 0, border=0, flag= wx.ALIGN_CENTER_VERTICAL)
        #--- The divergence ---
        self.boxSizerDivergence = wx.BoxSizer(orient=wx.HORIZONTAL)
        parent.Add(self.boxSizerDivergence, flag=wx.EXPAND)
        self.boxSizerDivergence.Add(self.textCtrlDivergence, 1, border=0, flag=wx.EXPAND)
        self.boxSizerDivergence.Add(self.staticDivergenceLabel2, 0, border=0, flag= wx.ALIGN_CENTER_VERTICAL)
        parent.Add(wx.Size(8.8,8.8))
        parent.Add(self.checkUseEquivalent, 0, border=0, flag= wx.ALIGN_CENTER_VERTICAL)
        
    def _init_coll_boxSizerAll_Items(self, parent):
        parent.Add(self.flexGridSizerTop, 0, border=3,
              flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM | wx.EXPAND)
        parent.Add(self.notebook, 1, border=0, flag=wx.EXPAND | wx.SHRINK)

    def _init_coll_gridSizerHKL_Items(self, parent):
        parent.Add(self.textCtrlH, 1, border=0, flag=wx.EXPAND|wx.SHRINK)
        parent.Add(self.textCtrlK, 1, border=0, flag=wx.EXPAND|wx.SHRINK)
        parent.Add(self.textCtrlL, 1, border=0, flag=wx.EXPAND|wx.SHRINK)

    def _init_sizers(self):
        self.boxSizerAll = wx.BoxSizer(orient=wx.VERTICAL)
        self.boxSizerPredicted = wx.BoxSizer(orient=wx.VERTICAL)
        self.boxSizerReal = wx.BoxSizer(orient=wx.VERTICAL)

        #The scroller with the default button
        self.boxSizerScrollWindow = wx.BoxSizer(orient=wx.VERTICAL)
        self.boxSizerScrollWindow.Add(self.buttonPlace, 0, border=8, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)

        self.boxSizerScrollWindowReal = wx.BoxSizer(orient=wx.VERTICAL)

        # self.flexGridSizerTop = wx.FlexGridSizer(cols=2, hgap=2, rows=3, vgap=3)
        self.flexGridSizerTop = wx.FlexGridSizer(5, 2, 3 ,2)
        self.flexGridSizerTop.SetMinSize(wx.Size(100, 87))

        # self.gridSizerHKL = wx.GridSizer(cols=3, hgap=2, rows=1, vgap=0)
        self.gridSizerHKL = wx.GridSizer(1, 3, 0, 2)

        self._init_coll_boxSizerAll_Items(self.boxSizerAll)
        self._init_coll_flexGridSizerTop_Items(self.flexGridSizerTop)
        self._init_coll_gridSizerHKL_Items(self.gridSizerHKL)

        #The predicted and real windows
#        self.boxSizerPredicted.AddWindow(self.staticTextTimesMeasured, 0, border=4, flag=wx.LEFT | wx.EXPAND)
        self.boxSizerPredicted.Add(wx.StaticLine(parent=self.windowPredicted), flag=wx.EXPAND)
        self.boxSizerPredicted.Add(self.scrolledWindowMeasurements, 1, border=0, flag=wx.SHRINK | wx.EXPAND)
#        self.boxSizerReal.AddWindow(self.staticTextTimesRealMeasured, 0, border=4, flag=wx.LEFT | wx.EXPAND)
        self.boxSizerReal.Add(wx.StaticLine(parent=self.windowReal), flag=wx.EXPAND)
        self.boxSizerReal.Add(self.scrolledWindowRealMeasurements, proportion=1, border=0, flag=wx.SHRINK | wx.EXPAND)

        self.windowPredicted.SetSizer(self.boxSizerPredicted)
        self.windowReal.SetSizer(self.boxSizerReal)
        self.SetSizer(self.boxSizerAll)
        self.scrolledWindowMeasurements.SetSizer(self.boxSizerScrollWindow)
        self.scrolledWindowRealMeasurements.SetSizer(self.boxSizerScrollWindowReal)
        self.boxSizerPredicted.Layout()
        self.boxSizerReal.Layout()
        self.scrolledWindowMeasurements.Layout()

    def _init_ctrls(self, prnt):
        wx.Panel.__init__(self, id=wxID_PANELREFLECTIONINFO,
              name='PanelReflectionInfo', parent=prnt, pos=wx.Point(1874, 552),
              size=wx.Size(250, 394), style=wx.TAB_TRAVERSAL)
        self.SetClientSize(wx.Size(250, 394))
        self.SetAutoLayout(True)

        #Must create notebook first
        self.notebook = wx.Notebook(parent=self)
        self.notebook.SetAutoLayout(False)

        #Window holds the predicted measurement list
        self.windowPredicted = wx.Panel(parent=self.notebook, id=wx.NewId())
        self.windowPredicted.SetAutoLayout(False)

        self.scrolledWindowMeasurements = wx.ScrolledWindow(id=wxID_PANELREFLECTIONINFOSCROLLEDWINDOWMEASUREMENTS,
              name='scrolledWindowMeasurements', parent=self.windowPredicted, pos=wx.Point(0,
              118), size=wx.Size(PanelReflectionMeasurement.DEFAULT_WIDTH, 50), style=wx.VSCROLL | wx.HSCROLL)

#        self.staticTextTimesMeasured = wx.StaticText(id=wxID_PANELREFLECTIONINFOSTATICTEXTTIMESMEASURED,
#              label=u'Reflection was predicted 3 times:',
#              name=u'staticTextTimesMeasured', parent=self.windowPredicted, style=wx.ALIGN_CENTRE)
#        self.staticTextTimesMeasured.Center(wx.HORIZONTAL)
#        self.staticTextTimesMeasured.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL,
#              wx.BOLD, False, u'Sans'))
#
#        self.staticTextTimesRealMeasured = wx.StaticText(id=wx.NewId(),
#                label=u'Reflection was measured 3 times:', pos=wx.Point(0, 0),
#                parent=self.windowReal, style=0*wx.ALIGN_CENTRE)
#        self.staticTextTimesRealMeasured.Center(wx.HORIZONTAL)
#        self.staticTextTimesRealMeasured.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL,
#              wx.BOLD, False, u'Sans'))


        #Window holds the real measurement list
        self.windowReal = wx.Panel(parent=self.notebook, id=wx.NewId(), pos=wx.Point(0,0), size=wx.Size(0,0))
        self.windowReal.SetAutoLayout(False)

        self.scrolledWindowRealMeasurements = wx.ScrolledWindow(id=wx.NewId(),
            parent=self.windowReal, style=wx.VSCROLL | wx.HSCROLL)



        self.staticTextHKLLabel = wx.StaticText(id=wxID_PANELREFLECTIONINFOSTATICTEXTHKLLABEL,
              label='Enter HKL:', name='staticTextHKLLabel', parent=self,
              pos=wx.Point(6, 11), size=wx.Size(72, 17), style=0)

        self.staticTextQLabel = wx.StaticText(id=wxID_PANELREFLECTIONINFOSTATICTEXTQLABEL,
              label='Q-vector:', name='staticTextQLabel', parent=self,
              pos=wx.Point(6, 41), size=wx.Size(72, 17), style=0)
        self.staticTextQLabel.SetAutoLayout(True)

        self.staticTextDlabel = wx.StaticText(id=wxID_PANELREFLECTIONINFOSTATICTEXTDLABEL,
              label='d-spacing:', name='staticTextDlabel', parent=self,
              pos=wx.Point(6, 71), size=wx.Size(72, 17), style=0)

        self.textCtrlH = wx.TextCtrl(id=wxID_PANELREFLECTIONINFOTEXTCTRLH,
              name='textCtrlH', parent=self, pos=wx.Point(80, 6),
              size=wx.Size(30, 27), style=0, value='0')

        self.textCtrlK = wx.TextCtrl(id=wxID_PANELREFLECTIONINFOTEXTCTRLK,
              name='textCtrlK', parent=self, pos=wx.Point(162, 6),
              size=wx.Size(30, 27), style=0, value='0')

        self.textCtrlL = wx.TextCtrl(id=wxID_PANELREFLECTIONINFOTEXTCTRLL,
              name='textCtrlL', parent=self, pos=wx.Point(244, 6),
              size=wx.Size(30, 27), style=0, value='0')

        self.textCtrlQ = wx.TextCtrl(id=wxID_PANELREFLECTIONINFOTEXTCTRLQ,
              name='textCtrlQ', parent=self, pos=wx.Point(80, 36),
              size=wx.Size(100, 27), style=wx.TE_READONLY, value='0 ,0, 0')
        self.textCtrlQ.Enable(True)
        self.textCtrlQ.SetEditable(False)
        self.textCtrlQ.SetFont(wx.Font(11, 76, wx.NORMAL, wx.NORMAL, False, 'Courier'))
        self.textCtrlQ.SetToolTip('q-vector coordinates (x,y,z) corresponding to this reflection.')

        self.textCtrlDspacing = wx.TextCtrl(id=wxID_PANELREFLECTIONINFOTEXTCTRLDSPACING,
              name='textCtrlDspacing', parent=self, pos=wx.Point(80, 66),
              size=wx.Size(100, 27), style=0, value='0')
        self.textCtrlDspacing.SetEditable(False)
        self.textCtrlDspacing.SetBackgroundStyle(wx.BG_STYLE_SYSTEM)
        self.textCtrlDspacing.SetToolTip('d-spacing corresponding to this reflection.')
        self.textCtrlDspacing.SetWindowVariant(wx.WINDOW_VARIANT_NORMAL)
        self.textCtrlDspacing.SetFont(wx.Font(11, 76, wx.NORMAL, wx.NORMAL, False, 'Courier'))


        self.staticDivergenceLabel = wx.StaticText(label='Divergence:', name='staticDivergenceLabel', parent=self,
              pos=wx.Point(6, 41),  style=0)
        self.textCtrlDivergence = wx.TextCtrl(name='textCtrlDivergence', parent=self, pos=wx.Point(80, 36),
              size=wx.Size(100, 27), value='0.00')
        self.textCtrlDivergence.Enable(True)
        self.textCtrlDivergence.Bind(wx.EVT_TEXT, self.OnTextCtrlDivergence)
        self.textCtrlDivergence.SetToolTip('Half-width of the divergence of the scattered beam, in degrees.')

        self.staticDivergenceLabel2 = wx.StaticText(label=' deg. half-width ', name='staticDivergenceLabel2', parent=self,
              pos=wx.Point(6, 41),  style=0)

        self.buttonPlace = wx.Button(label=' Try to place reflection on a detector... ',
              parent=self.scrolledWindowMeasurements, pos=wx.Point(128, 62), size=wx.Size(200, 30), style=0)
        self.buttonPlace.Bind(wx.EVT_BUTTON, self.OnButtonPlace)
        self.buttonPlace.SetToolTip("Open the reflection placer, to try to put the reflection on a detector by changing sample orientation.")
        self.buttonPlace.Show()

        self.checkUseEquivalent = wx.CheckBox(label='Show equivalent HKL also',
              parent=self, pos=wx.Point(128, 62), size=wx.Size(200, 30), style=0)
        self.checkUseEquivalent.SetToolTip("Include HKL peaks that are equivalent to the main HKL, based on crystal symmetry, in the list of measurements")
        self.checkUseEquivalent.Bind(wx.EVT_CHECKBOX, self.OnCheckUseEquivalent)


        #Notebook holding the predicted/real
        self.notebook.AddPage(self.windowPredicted, "Predicted", select=True)
        self.notebook.AddPage(self.windowReal, "Real", select=False)

        self._init_sizers()

    #----------------------------------------------------------------------------------
    def __init__(self, parent):
        self._init_ctrls(parent)
        #Attributes that should exist
        self.refl = None
        self._inside_set_reflection = False
        self.hkl_static_texts = [ [], [] ]

        #Fixing layout
        self.flexGridSizerTop.AddGrowableCol(1)
        #Settings to allow scrolling.
        for scrollwin in [self.scrolledWindowMeasurements, self.scrolledWindowRealMeasurements]:
            scrollwin.SetAutoLayout(True)
            scrollwin.EnableScrolling(False, True)
            scrollwin.SetScrollRate(5, 10)
            
        # self.boxSizerScrollWindow.SetVirtualSizeHints(self.scrolledWindowMeasurements)
    ##        scrollwinself.boxSizerAll.SetSize((660, 400))

        #Create an empty list of the measurement panels
        self.measure_panels = [ [], [] ]

        #Bind text events
        self.hkl_textCtls = [self.textCtrlH, self.textCtrlK, self.textCtrlL]
        for (i, ctl) in enumerate(self.hkl_textCtls):
            ctl.Bind(wx.EVT_TEXT, self.OnTextHKLEvent)
            ctl.SetToolTip('Enter the %s index of the reflection you are looking for.' % ('H','K','L')[i])

        #For calling observers
        self.observers = []

        #Set some values
        self.textCtrlDivergence.SetValue("%.3f" % model.config.cfg.reflection_divergence_degrees)

        #Subscribe to messages
        model.messages.subscribe(self.update_data, model.messages.MSG_EXPERIMENT_REFLECTIONS_CHANGED)

    #----------------------------------------------------------------------------------------------
    def __del__(self):
        #Clean up messages
        model.messages.unsubscribe(self.update_data, model.messages.MSG_EXPERIMENT_REFLECTIONS_CHANGED)

    #----------------------------------------------------------------------------------------------
    def update_data(self, *args):
        """Called when the reflections have been re-calculated."""
        if not self.refl is None:
            (h,k,l) = self.refl.hkl
            #Find the new reflection that has the same HKL
            self.set_hkl(h,k,l, update_textboxes=False)
            #We also manually have to call any observers of this 'new' hkl
            self.call_observers()


    #----------------------------------------------------------------------------------
    def add_observer(self, function):
        """Add an observer function that will be triggered whenever the HKL value
        is changed by the user.

        Parameters:
            function: callback function, that accepts 1 parameter: refl, a Reflection object.
        """
        self.observers.append(function)

    #----------------------------------------------------------------------------------
    def remove_observer(self, function):
        """Remove a previously added HKL change observer."""
        if function in self.observers:
            self.observers.remove(function)

    #----------------------------------------------------------------------------------
    def call_observers(self):
        """Call all the observers attached to this panel."""
        for function in self.observers:
            if not function is None:
                if callable(function):
                    #Have wx do the call after GUI events here have processed
                    wx.CallAfter(function, self.refl)

    #----------------------------------------------------------------------------------
    def set_reflection_measurements(self, refl):
        """Set the gui to display the given reflection object.

        Parameters:
            refl: Reflection object being displayed. Can be None for no reflection.
            real_mode: bool, True to do the real measurements, false for the predicted ones.
        """
        #@type refl Reflection
        
        for real_mode in [False, True]:

            #Settings to reuse
            scrollwin = [self.scrolledWindowMeasurements, self.scrolledWindowRealMeasurements][real_mode]
            sizer = [self.boxSizerScrollWindow, self.boxSizerScrollWindowReal][real_mode]

            min_panel_size = wx.Size(PanelReflectionMeasurement.DEFAULT_WIDTH, PanelReflectionMeasurement.DEFAULT_HEIGHT)

            #Do we look for equivalent reflections (due to symmetry)?
            if self.checkUseEquivalent.GetValue():
                refls = model.experiment.exp.get_equivalent_reflections(refl)
            else:
                #Make the single reflection into a list
                refls = [refl]

            #Make sure there are no Nones in the list
            while None in refls:
                refls.remove(None)

            #Count the measurements
            num_total_measurements = 0
            for refl in refls:
                if real_mode:
                    num_total_measurements += len(refl.real_measurements)
                    self.notebook.SetPageText(1, "Real Measurements: %d" % num_total_measurements)
                else:
                    num_total_measurements += len(refl.measurements)
                    self.notebook.SetPageText(0, "Predicted: %d" % num_total_measurements)


            #Neat trick to make the last word plural
#            if real_mode:
#                self.staticTextTimesRealMeasured.SetLabel("Reflection was measured %d time%s:" % (num_total_measurements, ('s', '')[int(num_measurements==1)]) )
#            else:
#                self.staticTextTimesMeasured.SetLabel("Reflection was predicted %d time%s:" % (num_total_measurements, ('s', '')[int(num_measurements==1)]) )

            #Remove all static text label
            for txt in self.hkl_static_texts[real_mode]:
                sizer.Remove(txt)
                txt.Close()
            self.hkl_static_texts[real_mode] = []

            #i counts the measurement number SHOWN in the windo
            i = 0
            for (reflection_number, refl) in enumerate(refls):
                #How many measurements in this one?
                if real_mode:
                    num_measurements = len(refl.real_measurements)
                else:
                    num_measurements = len(refl.measurements)

                #Add a static text label for the hkl
                s = "As HKL %d,%d,%d:" % refl.hkl
                if num_measurements == 0:
                     s += [" (not predicted)",  " (not measured)"][real_mode]
                    
                txt = wx.StaticText(parent=scrollwin, label=s)
                self.hkl_static_texts[real_mode].append(txt)
                #Slip it in the right spot
                sizer.Insert(i+reflection_number+[1,0][real_mode], txt, 0, border=4, flag=wx.EXPAND | wx.LEFT | wx.RIGHT)

                #Now do all the measurements
                for refl_measurement_number in range(num_measurements):
                    if i >= len(self.measure_panels[real_mode]):
                        #Need to create a new one
                        new_panel = PanelReflectionMeasurement(scrollwin)
                        if (i % 2)==0:
                            new_panel.SetBackgroundColour(gui_utils.TEXT_BACKGROUND_COLOUR_GOOD)
                        sizer.AddWindow(new_panel, 1, border=2, flag=wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM | wx.EXPAND | wx.SHRINK)
                        new_panel.SetClientSize(min_panel_size)
                        new_panel.SetMinSize(min_panel_size)
                        scrollwin.SetMinSize(min_panel_size)
                        sizer.SetMinSize(min_panel_size)
                        self.measure_panels[real_mode].append(new_panel)
                    #Make sure it can be seen
                    self.measure_panels[real_mode][i].Show(True)

                    #And set its data
                    if real_mode:
                        meas = refl.real_measurements[refl_measurement_number]
                    else:
                        meas = ReflectionMeasurement(refl, refl_measurement_number, divergence_deg=model.config.cfg.reflection_divergence_degrees)
                    self.measure_panels[real_mode][i].set_measurement(refl, meas)

                    #Next one in the list
                    i += 1

            #Now hide any excess ones
            for i in range( num_total_measurements, len(self.measure_panels[real_mode])):
                self.measure_panels[real_mode][i].Show(False)

            #The button.
            if not real_mode:
                if num_total_measurements==0:
                    self.buttonPlace.Show()
                else:
                    self.buttonPlace.Hide()

            #For scrolling
            sizer.Layout()
            scroll_size = sizer.GetMinSize()
    #        scroll_size[0] = PanelReflectionMeasurement.MIN_WIDTH
            scrollwin.SetVirtualSize(scroll_size )
            scrollwin.Layout()
            self.Update()

        

    #----------------------------------------------------------------------------------
    def set_hkl(self, h, k, l, update_textboxes=True):
        """Make the panel show the given hkl reflection.

        Parameters:
            h,k,l: reflection indices
            update_textboxes: will set the value in the textboxes
        """
        refl = model.experiment.exp.get_reflection(h, k, l)
        self.set_reflection(refl, update_textboxes=update_textboxes)

    #----------------------------------------------------------------------------------
    def set_reflection(self, refl, update_textboxes=True):
        """Make the panel show the given reflection.

        Parameters:
            refl: Reflection object to show
            update_textboxes: will set the value in the hkl textboxes
        """
        self._inside_set_reflection = True
        
        self.refl = refl
        #Put the text in the boxes
        if update_textboxes:
            for i in range(3):
                if refl is None:
                    self.hkl_textCtls[i].SetValue( "None" )
                else:
                    self.hkl_textCtls[i].SetValue( "%d" % ( refl.hkl[i] ) )

                
        #Rest of the GUI
        if refl is None:
            self.textCtrlDspacing.SetValue( "None" )
            self.textCtrlQ.SetValue( "None" )
            for ctl in self.hkl_textCtls:
                ctl.SetBackgroundColour(gui_utils.TEXT_BACKGROUND_COLOUR_BAD)
        else:
            self.textCtrlDspacing.SetValue( "%8.3f ang." % refl.get_d_spacing() )
            self.textCtrlQ.SetValue( "%7.2f,%6.2f,%6.2f" % tuple(refl.q_vector.ravel()) )
            for ctl in self.hkl_textCtls:
                ctl.SetBackgroundColour(gui_utils.TEXT_BACKGROUND_COLOUR_GOOD)


        #This'll update the measurements list
        self.set_reflection_measurements(refl)

        self._inside_set_reflection = False


    #----------------------------------------------------------------------------------
    def OnTextHKLEvent(self, event):
        """Called when user types in the HKL text boxes"""
        #Avoid calling this at wrong times
        if self._inside_set_reflection:
            return
        
        #Extract the hkl values, use a crazy number to signal a bad input
        hkl = [-10000000]*3
        for i in range(3):
            try:
                hkl[i] = int(round(float(self.hkl_textCtls[i].GetValue())))
            except ValueError:
                pass

        #Change the rest of the GUI (but not the boxes)
        self.set_hkl(hkl[0], hkl[1], hkl[2], update_textboxes=False)

        #Call any observers of this new hkl
        self.call_observers()
        event.Skip()

    def OnTextCtrlDivergence(self, event):
        """Called when typing in values for divergence."""
        try:
            #Get the divergence in degrees
            div = float(self.textCtrlDivergence.GetValue())
            #Save it in the configuration
            model.config.cfg.reflection_divergence_degrees = div
            #Update the measurements.
            self.set_reflection_measurements(self.refl)
            self.textCtrlDivergence.SetBackgroundColour(gui_utils.TEXT_BACKGROUND_COLOUR_GOOD)
        except ValueError:
            self.textCtrlDivergence.SetBackgroundColour(gui_utils.TEXT_BACKGROUND_COLOUR_BAD)
            
    def OnButtonPlace(self, event):
        reflection_placer.show_placer_frame(self, self.refl, None)
        event.Skip()

    def OnCheckUseEquivalent(self, event):
        #Update the measurements.
        self.set_reflection_measurements(self.refl)
        event.Skip()






if __name__ == "__main__":
    model.instrument.inst = model.instrument.Instrument()
    model.experiment.exp = model.experiment.Experiment(model.instrument.inst)
    model.experiment.exp.initialize_reflections()
    from . import gui_utils
    (app, pnl) = gui_utils.test_my_gui(PanelReflectionInfo)
    app.frame.SetClientSize(wx.Size(300, 500))
    #@type refl Reflection
    refl = model.reflections.Reflection( (1,2,3), np.array([1,2,3]))
    for i in range(7):
        refl.measurements.append( (1,2,3,4,5,6) )
    for i in range(4):
        rrm = ReflectionRealMeasurement()
        rrm.detector_num = i
        rrm.integrated = i*11.0
        rrm.sigI = i*0.5
        rrm.wavelength = i+.23
        rrm.distance = i+.45
        rrm.horizontal = 10+i
        rrm.vertical = -10-i
        rrm.measurement_num = i+1000
        refl.real_measurements.append(rrm)

    pnl.set_reflection_measurements(refl)
    app.MainLoop()
