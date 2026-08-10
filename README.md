# QGIS-Processing-tools
Various scripts for the QGIS 3.x processing toolbox.

## Installation:

Just download the *.py file from "scripts" here - click the provided link and then the Download raw file icon:

<img src="images/download_raw.png" alt="Download raw file icon">

and copy the file to the scripts subfolder in your QGIS user profile - the path is usually like this:

Windows: %APPDATA%\QGIS\QGIS3\profiles\default\processing\scripts

Linux: ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts

macOS: ~/Library/Application Support/QGIS/QGIS3/profiles/default/processing/scripts

Or just go to the main QGIS menu toolbar and choose *Settings / User Profiles / Open Active Profile Folder* - the profile folder will open in the default file manager.

## Safecast Point Loader

Loads Safecast measurement points (bGeigie imports) for the <b>current map canvas extent</b>.

<img src="images/safecastpointloader.jpg" alt="screenshot of QGIS Safecast Point Loader window and loaded data" width="800"/>

* Point layer in EPSG:4326
* Embedded default symbology (dose rate classes)
* Supports temporary layer or file output (GeoPackage, GeoJSON, Shapefile…)

The script uses an endpoint from the Safecast New Map (https://simplemap.safecast.org/) - the goal was to be able to view and work with Safecast data (bGeigie, CzechRad devices) without having to download the entire large dataset.


DISCLAIMER:

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
