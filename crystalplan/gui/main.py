#!/usr/bin/env python
"""CrystalPlan GUI Main file.
Includes GUI launcher, logger, error handler."""
#Boa:App:CrystalPlanApp

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id: CrystalPlan.py 1127 2010-04-01 19:28:43Z 8oz $

#--- General Imports ---

import sys
import os
import os.path
import traceback
import datetime
from optparse import OptionParser
import wx


import os
os.environ['ETS_TOOLKIT'] = 'wx'

from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'wx'   


#-------------------------------------------------------------------------
# The following is generated by BOA Constructor IDE
modules ={'detector_views': [0, '', 'detector_views.py'],
 'dialog_preferences': [0, '', 'dialog_preferences.py'],
 'dialog_startup': [0, '', 'dialog_startup.py'],
 'display_thread': [0, '', 'display_thread.py'],
 'experiment': [0, '', 'model/experiment.py'],
 'frame_main': [1, 'Main frame of Application', 'frame_main.py'],
 'frame_qspace_view': [0, '', 'frame_qspace_view.py'],
 'frame_reflection_info': [0, '', 'frame_reflection_info.py'],
 'frame_test': [0, '', 'frame_test.py'],
 'goniometer': [0, '', 'model/goniometer.py'],
 'gui_utils': [0, '', 'gui_utils.py'],
 'instrument': [0, '', 'model/instrument.py'],
 'messages': [0, '', 'model/messages.py'],
 'panel_add_positions': [0, '', 'panel_add_positions.py'],
 'panel_detectors': [0, '', 'panel_detectors.py'],
 'panel_experiment': [0, '', 'panel_experiment.py'],
 'panel_goniometer': [0, '', 'panel_goniometer.py'],
 'panel_positions_select': [0, '', 'panel_positions_select.py'],
 'panel_qspace_options': [0, '', 'panel_qspace_options.py'],
 'panel_reflection_info': [0, '', 'panel_reflection_info.py'],
 'panel_reflection_measurement': [0, '', 'panel_reflection_measurement.py'],
 'panel_reflections_view_options': [0,'','panel_reflections_view_options.py'],
 'panel_sample': [0, '', 'panel_sample.py'],
 'plot_panel': [0, '', 'plot_panel.py'],
 'scd_old_code': [0, '', 'scd_old_code.txt'],
 'slice_panel': [0, '', 'slice_panel.py']}


#The background display thread
global background_display
background_display = None


#-------------------------------------------------------------------------
#-------------------- LOGGING AND ERROR HANDLING -------------------------
#-------------------------------------------------------------------------
#(with is in python 2.6)

#-------------------------------------------------------------------------
class OutWrapper(object):
    """Class wraps the standard output and logs it to a file."""
    def __init__(self, realOutput, logFileName):
        self._realOutput = realOutput
        self._logFileName = logFileName
        print("Logging standard output to", logFileName)

    def _log(self, text):
        """Add a line of text to the log file."""
        with open(self._logFileName, 'a') as logFile:
            logFile.write(text)

    def flush(self):
        """Flush out stdout."""
        self._realOutput.flush()

    def write(self, text):
        """Log and output to stdout the text to print out."""
        self._log(text)
        self._realOutput.write(text)

    def write_error(self, text):
        """Log and output error message."""
        self._log(text)
        sys.stderr.write(text)


#-------------------------------------------------------------------------
def excepthook(type, value, tb, thread_information="Main Loop"):
    """Uncaught exception hook. Will log the exception and display it
    as a message box to the user."""
    global out_wrapper
    message = 'Uncaught exception (from %s):\n-----------------------\n' % thread_information
    message += ''.join(traceback.format_exception(type, value, tb))
    message += '-----------------------\n\n'
    #Also log the exception (and output to stdout)
    out_wrapper.write_error("\n"+message)
    #And show a messagebox for the user.
    extra_message = "This exception has been logged to " + out_wrapper._logFileName
    extra_message += "\n\nYou can attempt to continue your work, but you may run into other errors/problems if you do."
    #TODO: Make into a nicer dialog, maybe submit a bug report directly?
    wx.CallAfter(wx.MessageBox, message + extra_message,
        caption="Unhandled Exception from %s" % thread_information, style=wx.OK | wx.ICON_ERROR)




#-------------------------------------------------------------------------
class CrystalPlanApp(wx.App):
    def OnInit(self):
        #Create the main GUI frame
        from crystalplan.gui import frame_main
        from crystalplan.gui import frame_qspace_view
        self.main = frame_main.FrameMain(None)
        self.main.Show()
        #Set it on top
        self.SetTopWindow(self.main)
        #Also, we show the q-space coverage window
        # frame_qspace_view.get_instance(self.main).Show()
        return True


#-------------------------------------------------------------------------
def launch_gui(inelastic, hb3a):
    """Launch the CrystalPlan GUI.

    Parameters:
        inelastic: boolean, to indicate whether the instrument is for inelastic scattering.
        hb3a: boolean, for the HB3A beamline
        """

    from crystalplan import CrystalPlan_version
        
    #Since imports take a while, print out this status line first.
    print("-------------- %s %s GUI is starting -----------------" % (CrystalPlan_version.package_name, CrystalPlan_version.version))
    
    #--- GUI Imports ---
    from crystalplan.gui import display_thread
    import wx
    from crystalplan import model


    #Create a StdOut wrapper
    global out_wrapper
    out_wrapper = OutWrapper(sys.stdout, r'CrystalPlan_Log_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt" )
    sys.stdout = out_wrapper

    #Attach our exception hook
    sys.excepthook = excepthook

    
    #TODO: Here pick the latest instrument, load other configuration
    #Make the goniometers
    model.goniometer.initialize_goniometers()

    #Ok, create the instrument
    if hb3a:
        print("Initializing HB3A scattering instrument.")
        model.instrument.inst = model.instrument.InstrumentFourCircle()
        g = model.goniometer.HB3AGoniometer()
        model.instrument.inst.set_goniometer(g)
    elif inelastic:
        print("Initializing inelastic scattering instrument.")
        model.instrument.inst = model.instrument.InstrumentInelastic(model.config.cfg.default_detector_filename)
        model.instrument.inst.set_goniometer(model.goniometer.Goniometer())
    else:
        print("Initializing elastic scattering instrument.")
        model.instrument.inst = model.instrument.Instrument(model.config.cfg.default_detector_filename)
        g = model.goniometer.TopazAmbientGoniometer(wavelength_control=False)
        model.instrument.inst.set_goniometer(g)
        
    model.instrument.inst.make_qspace()

    #Initialize the instrument and experiment
    model.experiment.exp = model.experiment.Experiment(model.instrument.inst)
    model.experiment.exp.crystal.point_group_name = model.crystals.get_point_group_names(long_name=True)[0]

    #Initialize what needs to.
    model.experiment.exp.initialize_volume_symmetry_map()
    model.experiment.exp.initialize_reflections()
    model.experiment.exp.recalculate_reflections(None)

    #Initialize the application
    application = CrystalPlanApp(0)

    #Start the thread that monitors changes to the q-space coverage calculation.
    if True: #To try it with and without
        background_display = display_thread.DisplayThread()
        display_thread.thread_exists = True
    else:
        display_thread.thread_exists = False


    try:
        #Start the GUI loop
        application.MainLoop()
    except:
        #Catch the latest error and report it
        xc = traceback.format_exception(*sys.exc_info())
        wx.MessageBox("Exception caught in MainLoop!\n\n" + ''.join(xc))


    #Exit the program and do all necessary clean-up.
    print("Exiting %s %s. Have a nice day!" % (CrystalPlan_version.package_name, CrystalPlan_version.version))
    background_display.abort()



def handle_arguments_and_launch(InstalledVersion):
    #Parameter: InstalledVersion: True if launching from the installed crystalplan.py scrip
    #           False if launching from the gui/ folder

#    if InstalledVersion:
#        import CrystalPlan
#        print dir(CrystalPlan)
#        from CrystalPlan import *
#        print "Version ", CrystalPlan_version.version
#    else:
    #Manipulate the PYTHONPATH to put model directly in view of it
    #   This way, "import model" works.
    # sys.path.insert(0, "..")
    from crystalplan import CrystalPlan_version

    # --- Handle Command Line Arguments -----
#    usage = "---- Welcome to " + CrystalPlan_version.package_name + " v." + CrystalPlan_version.version + " ----\n\nUsage: %prog [options] arg1 arg2"
    parser = OptionParser(prog=CrystalPlan_version.package_name+".py", version="%s v.%s" % (CrystalPlan_version.package_name, CrystalPlan_version.version))
    parser.add_option("-t", "--test", dest="test",
                     action="store_true", default=False,
                     help="perform a suite of unit tests on the software")
    parser.add_option("-i", "--inelastic", dest="inelastic",
                     action="store_true", default=False,
                     help="simulate an inelastic scattering instrument")
    parser.add_option("-3", "--hb3a", dest="hb3a",
                     action="store_true", default=False,
                     help="simulate HFIR beamline HB3A")
    (options, args) = parser.parse_args()

    if options.test:
        #Run unit tests
        if InstalledVersion:
            #Go to the model dir.
            os.chdir( os.path.join( os.path.dirname(__file__), "../model"))
        else:
            os.chdir("../model")
        os.system("python test_all.py")
    else:
        #Start the GUI
        launch_gui(inelastic=options.inelastic, hb3a=options.hb3a)




#---------------- MAIN -------------------------------------------
if __name__=="__main__":
    handle_arguments_and_launch(InstalledVersion=False)