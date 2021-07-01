"""Version information for CrystalPlan"""
# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

version = '2.0.0'
package_name = 'crystalplan'
description = \
"""CrystalPlan is an experiment planning tool for crystallography. """+\
"""You can choose an instrument and supply your sample's lattice """ +\
"""parameters to simulate which reflections will be measured, by which """+\
"""detectors and at what wavelengths."""

license = """Enter license text here."""
author = "Janik Zikovsky"
author_email = "zikovskyjl@ornl.gov"
url = 'https://github.com/neutrons/CrystalPlan'
copyright = '(C) 2010'

#Path to icons, relative to gui scripts path
icon_file = "icons/CrystalPlan_icon.png"
icon_file_config = "icons/CrystalPlan_icon_config.png"
icon_file_3d = "icons/CrystalPlan_icon_3d.png"
icon_file_optimizer = "icons/CrystalPlan_icon_optimizer.png"

if __name__ == "__main__":
    print(package_name, version)