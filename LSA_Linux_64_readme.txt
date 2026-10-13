This release note and the software that accompanies it are (c)Copyright 2026
Broadcom Inc or its suppliers, and may only be installed and used in accordance
with the license that accompanies the software. All rights reserved.

This Software is furnished under license and may only be used or copied in accordance with
the terms of that license. No license, express or implied, by estoppel or otherwise,
to any intellectual property rights is granted by this document. The Software is subject
to change without notice, and should not be construed as a commitment by Broadcom Inc
or its suppliers to market, license, sell or support any product or technology.
Unless otherwise provided for in the license under which this Software is provided,
the Software is provided AS IS, with no warranties of any kind, express or implied.
Except as expressly permitted by the Software license, none of its suppliers assumes any
responsibility or liability for any errors or inaccuracies that may appear herein.
Except as expressly permitted by the Software license, no part of the Software maybe
reproduced, stored in a retrieval system, transmitted in any form, or distributed by any
means without the express written consent of Broadcom Inc.

=====================
Supported Controllers
=====================
Broadcom 3916 SAS3/PCIe4 Tri-mode RAID on Chip, SAS 3516 Ventura based MegaRAID and iMR, SAS 3108 (Invader) based MegaRAID and iMR, SAS 3008 (Fury) based HBAs,
Wellsburg & Lewisburg SATA chipset based Software RAID, SAS3816 based IOC, SAS3808 based IOC, SAS3008 based HBAs, Initiator-Target 3 (IT3) controller
9660 Family RAID Adapters, 9670 Family RAID Adapters, 9600 Family eHBA Adapters, 9620 Family eHBA Adapters

===================
Package Information
===================
LSA version = 008.017.010.000
OS supported =  RHEL 9.5, RHEL 9.6, RHEL 9.7, RHEL 10, RHEL 10.1, SLES 15 SP5, SLES 15 SP6, SLES 16 ,SLES 15 SP7, Ubuntu 22.04 LTS, Ubuntu 24.04 LTS, OpenEuler 24.03
Language(s) supported = English
This package is intended only for x64 system (or) Platform.

This package contains gcc_8.3.x and gcc_11.2.x. Below are the corresponding OS support:

gcc_8.3.x -  SLES 15 SPx, SLES 16 SPx 
gcc_11.2.x - RHEL 10.x,RHEL 9.x, Ubuntu 24.04 LTS, Ubuntu 22.04 LTS, OpenEuler 24.03

NOTE:
gcc_8.3.x -> LSA Installer in this folder supports gcc_8.3.x 
gcc_11.2.x ->LSA Installer in this folder supports gcc_11.2.x 

=========================
Pre-Requisites
=========================

1. Prior to the installation of LSA, we need to install OpenSLPv2.0.0 which is a Pre-Requisite. So please install it from the below location and install LSA.
   Please make sure libslp.so.xx and slpd files are present in the system after OpenSLP installation.

http://www.openslp.org/download.html

   If OpenSLP is not installed, internally packaged OpenSLP binaries shall be installed in alternate location during LSA installation.
   User also has an option to continue with the LSA installation after proceeding with the installation of OpenSLP from the OS installation sources.

2. Soft links in Linux 64 bit: For RHEL/SLES on 64-bit platform(s), it is necessary to create the below soft links if openslp is not installed in "/usr/lib64/" or "/user/lib/" directory, before installing LSIStorageAuthority (LSA) 64-bit package.
    "ln -sf /usr/local/lib/libslp.so.1.0.0 /opt/lsi/LSIStorageAuthority/bin/libslp.so.1" or
    "ln -sf /usr/local/lib64/libslp.so.1.0.0 /opt/lsi/LSIStorageAuthority/bin/libslp.so.1"
    This is not necessary if internally packaged OpenSLP binaries is installed in alternate location during LSA installation.

3. An Instance of OpenSLP Was Already Installed, but LSA Is Unable to Display All the Registered Servers from the Remote Discovery page
   Restart the SLPD Services and LSA Service if LSA does not discover the servers from the Remote Discovery page
   a) For stopping the slpd use the command : killall slpd or /etc/init.d/slpd stop or systemctl stop slpd.service
   b) For starting the slpd use the command /etc/init.d/LsiSASH restart, where along with LSA service the slpd is also started.
   c) If the slpd is already installed as part of the OS package then use the command: /etc/init.d/slpd start or systemctl start slpd.service.

4. From RHEL 8+ the Desktop ICON Launching property is disabled by default. 
   User(s) needs to use either yum or DNF to install gnome-tweak-tool and enable the Desktop Shortcut feature to launch LSA.
5. By default chkconfig package is not present from RHEL 9. This package is required to auto start LSA service on system boot. Install chkconfig package before installing the LSA.
6. By default libnsl.so.2 is not present from RHEL 9 and Open Euler. LSA depends on the libnsl.so.2. Install libnsl.so.2 before installing the LSA.
7. Make sure no LSA_lib_utils.xx and LSA_lib_utils2.xx pacakges were installed prior to LSA installation

=========================
Open Source Usage
=========================
Here is the list of Open Source types that has been used in LSA.
Boost v1.0 , MIT, Open Market FastCGI, zlib , BSD, The dual OpenSSL and SSLeay, Apache v2.0
 
Further details can be found using the link: <IP_ADDRESS:Web Server Port/files/credits.html>

=========================
Known Restrictions/Issues
=========================
1. On some SLES setups, due to delay in DHCP IP assignment, SLP service cannot be started due to which LSA discovery shall fail on remote machines. Users may have to restart LSA services on remote system using command '/etc/init.d/LsiSASH restart' to overcome this issue. For SLES 12, there is a known issue (refer https://bugzilla.suse.com/show_bug.cgi?id=951225 for more details).
2. Default browser on RHEL crashes when upgrade/downgrade firmware using LSA
	To work around you can disable or configure SELinux. Refer the link to disable SELinux on RHEL. "https://access.redhat.com/solutions/3176"
3. For SLES15 and above platforms, one of the dependent rpms - 'insserv-compat' is required during installation/uninstallation. This is needed because LSA startup script is based on SysV/init script
    and insserv adds as a bridge between SysV/init script and systemctl.
4. LSA when launched with Linux Native Mozilla Firefox and kept idle for more than half an hour, LSA will become slow.
   Root Cause: Mozilla is sending multiple long poll calls on page refresh or moving across server landing and control console page.
   Similar bugs has been Raised with bugzilla, please find below the reference links
   https://bugzilla.mozilla.org/show_bug.cgi?id=1126689, https://bugzilla.mozilla.org/show_bug.cgi?id=1522781
   Work Around: Logout, Close the browser and relaunch the LSA.
5. When only IPv6 NIC is enabled (No IPv4), OpenSLP registration is failing for LSA with error code "-23" due to a bug in OpenSLP.
   Due to which LSA is not able to display the IPv6 address, instead of it will be showing the loop-back address (127.0.0.1).
   So please ensure we have at-least one IPv4 NIC is active so avoid the confusion related to the IP Address.
6. It is possible to get a time-out from server. This time-out error is generated at the back-end if resource providing the content takes more time.
	eg: Firmware flash, enclosure(s) insertion with more Foreign (or) UBAD (or) combination of Foreign and UBAD drives, 
	 Clear Configuration/Any operation- User(s) may see a time-out error (404 or 504) with large configuration (Can be Physical Drives (or) Virtual Drives).
	 This is due to an issue in underlying layer, and CLI can be used to overcome this user(s) need to follow below 
	 a.	Change the nginx fastcgi_read_timeout variable in <LSA_HOME>\server/conf/nginx.conf to "300"seconds. This value varies based on the configuration.
	 b.	Change the "listening_port_backlog" value in <LSA_HOME>\conf\LSA.conf to 2400
	 c.	Refresh the LSA page manually after waiting adequate time.
7. Recommendation is to clear the browser history every time user upgrades/downgrades or installs the software or when user modifies the default settings in any conf file
8. LSA displays connector and enclosure position as "-" in PD related events, in the case of corresponding element is removed from the FW stack
9. When heavy IOs are active, it is recommended NOT to perform "Download Server Report" as this may get delayed.
10. Once the drive gets removed from the stack, there is no data available corresponding to the drive in FW. In this case LSA displays the connector name as empty for drive removal event and the subsequent events.
11. Download Server Report option will be provided only for "Full Access" User(s) only.
12. HttpOnly flag won't be set for server ID cookie as it set from client(GWT) which won't support this link below for reference.as we are already blocking execution of external script execution by setting Content-Security-Policy.
http://researchhubs.com/post/computing/javascript/set-a-cookie-to-httponly-via-javascript.html
13. Sorting may not work in the span tab when a missing drive present in that span.
14. There is a communication failure between LSA server to few SMTP port with TLS communication - STARTTLS, which gives test and email notification failure.
15. Due to unintended changes brought in by the compiler Flags, repository shared object file is compiled with partial RELRO.
16. It is mandatory to verify all the "Mail Server" and "Email" tab's fields are correctly populated / entered, before triggering "Test Configuration" and "Save Settings".
Note: Password field would not be populated in GUI
17. It is recommended to set LD_LIBRARY_PATH to use the LSA console when LSA not able to find the relative path.
    export LD_LIBRARY_PATH="${INSTALL_ROOT}/bin:$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${INSTALL_ROOT}/plugins:$LD_LIBRARY_PATH"
    Assume INSTALL_ROOT is "/opt/lsi/LSIStorageAuthority"
18. Below CVE fixes has been part of the OpenSLP that is bundled along with LSA/RWC3 though some of the Scan tools will still display the below CVE's
CVE-2016-4912
CVE-2016-7567
CVE-2019-5544
19. Due to lower layer limitation, in the case of offline FW update, LSA not updating the health message or icon regarding system reboot required
20. User can not clear the configuration when VD(s)/JBOD(s) with OS/FS/Unknown Boot partition (cannot be read). In this case, user has to go to specific VD(s) and delete them.	
21. User is expected to refresh the browser on drive removal and insertion to see the updated data.
22. User(s) might see the "FAULT/DEAD" alert notification if there is any event pertaining to the "FAULT/DEAD".
    GUI might not have the provision for the user(s) to Configure this option as part of Alert Delivery settings, but user(s) by default receive this notification.
23. User(s) will not be able to see the PBLP component image and it's version details, if user(s) is trying to flash/upgrade the fw using the Vision(vsn) package.
24.During VD creation users will not be allowed to enter less than 1 MB size and user can not enter values in KB from GUI, but during adding VD to the existing DG user will be allowed to enter less than 1 MB from GUI and LSA server will fail it. 
24.a.Depending on controller max stripe size, Minimum VD size may vary and could be less than 1 MB. 
25.LSA will consider the VD health instead of VD status when showing the VD health icon from 7.22 onwards
26. Physical Drive/Controller/Enclosure properties "view" option may throw "This page isn’t working" error with Chrome browser.
27. During LSA installation/upgrade users may see the error "pubKey.asc: key 1 import failed" from RHEL 9 OS, though LSA gone through all the necessary signing process (Note: this error not seen in previous RHEL flavors), Users can ignore this error.
28. During VD creation adding drives some of the non-mixing drives row's style is not updating to disable look.
29. Due to the build-id Unique Identification of binaries, user can have only a single copy of SL library (libstorelibit*.so) installed across multiple applications. During installation, If user seen any conflict with the existing rpm's binary then remove the old rpm to proceed with current installation.
30. During Foreground initialization in progress, multiple VD selections might show stale operations like "Modify Properties" for a few seconds and disappear.
31.When heavy IOs are active, LSA will be slow  and user might see stale data. Please refresh the browser or Restart LSA service to get the updated data.
32.When user enable/disable controller, Controller will not be loaded/unloaded in LSA by default. This needs LSA service restart to get the updated controller list.
33. Client's debug logs (corpus) will not be part of "server report".
34. JBOD(s) sorting is not supported under the Make JBOD Secure table.
35. When user sees the error page 50x "try again" will work when resources are available else please Check LSAService and Nginxservice status.
36. If lower layer does not populate the corresponding element's property value then LSA displays those property value as 'NA' , '-' or the property itself will not be part of the UI screen.
37. When user performs  Foreign configuration import, LSA shows Clear button enabled in the case of drive re-provision, even though there is no foreign configuration found. Clicking on clear will fail the call.
38. There may be delayed response observed in LSA with operations performed on IR/IT Controller.
39. In Ubuntu, if the user encounters any errors during LSA Installation, one common cause is having two files with very similar names and identical contents, then the user should create a symbolic link to the other
    Below are the sample errors during installation:
       /sbin/ldconfig.real: /usr/local/lib/libldap_r-2.4.so.2 is not a symbolic link
       /sbin/ldconfig.real: /usr/local/lib/liblber-2.4.so.2 is not a symbolic link
       /sbin/ldconfig.real: /usr/local/lib/libldap-2.4.so.2 is not a symbolic link
    Steps to be taken care before Installtion of LSA for libldap* errors:      
    1) To check if the two files are the same, you can use the following command:
          cd /usr/local/lib
          diff libldap-2.4.so.2 libldap-2.4.so.2.10.12
    2) If files are the same, the `diff` command will not return any output.
    3) If files are the same delete libldap-2.4.so.2 and make a symbolic link to the other file with that name.
            sudo rm libldap-2.4.so.2
            sudo ln -s libldap-2.4.so.2.10.12 libldap-2.4.so.2
    Perform the same steps for other errors.
40. Sorting might not work properly with the Tape Drive present in the topology. However, users can filter the tape using media.
41. Following are the known vulnerabilities in glibc used in below packages
    gcc_4.8.x -> LSA Installer in this folder supports gcc_4.8.x & higher 
    (https://www.cybersecurity-help.cz/vdb/gnu/glibc/2.17/)
    gcc_8.3.x -> LSA Installer in this folder supports gcc_8.3.x & higher 
    (https://www.cybersecurity-help.cz/vdb/gnu/glibc/2.28/)
    gcc_11.2.x ->LSA Installer in this folder supports gcc_11.2.x & higher
    (https://www.cybersecurity-help.cz/vdb/gnu/glibc/2.32/)
42. For a PD with 0 size or a bad PD, LSA shows the size and sector size as "-."
43. For PerfIT, LSA might show the drive media type as HDD instead of SSD after the cable pull/push. It indicates correctly after the refresh.
=======================
Contents of the package
=======================
   LSA_Linux.zip
	x64 -- Contains files for 64-bit platforms

=========================
Installation Instructions
=========================
See Detailed installation instructions below:

1. Log in to the system as root or as a user with root privileges.
  Depending on the operating system and security settings, it may be necessary to
  install LSA using root rights. This may require that, log in as root and run the installer,
  or open a command prompt as root and run the installer via the command line,

2. LSA supports both interactive and non-interactive modes of installation.
	a. Interactive mode installation steps:
		1. Execute the command "./install.sh" from the installation disk.
		   For Ubuntu execute the command "./install_deb.sh" from the installation disk.
		2. License Agreement : enter y to continue, n to exit.
		3. Type of installation:
								1- for Gateway
								2- for StandAlone
								3- for DirectAgent
								4- for Light Weight Monitor(LWM).
		4. Enter Nginx Server port [1-65535] default port is 2463
		5. Enter LSA port [1-65535] default port is 9000

	b.Non-interactive or silent mode installation steps:
		1. Execute command "./install.sh [-options] [nginx_port] [LSA_port] [Alert_Notification]" from the installation disk.
		   For Ubuntu use "install_deb.sh" instead of "install.sh".
		2. The options are:
			-g for Gateway
			-s for StandAlone
			-d for DirectAgent
			-l for Light Weight Monitor(LWM)
		3. nginx_port and LSA_port must be in range [1-65535] and must be different.
		4.  Alert_Notification options:
			1=Since Last Shutdown
			2=Since Last Clear
			3=Since Last Reboot
			4=Since Newest
			if nginx_port, LSA_port and Alert_Notification is not specified in the command line the default values (Nginx default port 2463, LSA default port 9000 and Alert Notification value 1) will be used.

	c. Interactive upgrade instructions:
		1. Execute the command "./install.sh" from the installation disk.
		   For Ubuntu execute the command "./install_deb.sh" from the installation disk.
		2. License Agreement : enter y to continue, n to exit.
		3. Type of installation:
								1- for Gateway
								2- for StandAlone
								3- for DirectAgent
								4- for Light Weight Monitor(LWM).
		4. Enter Nginx Server port [1-65535] default port is 2463
		5. Enter LSA port [1-65535] default port is 9000

	d. Silent upgrade instructions:
		1. Execute "./install.sh [-option] [nginx_port] [LSA_port] [Alert_Notification]"
		   For Ubuntu use "install_deb.sh" instead of "install.sh".
		2. The options are:
			-g for Gateway
			-s for StandAlone
			-d for DirectAgent
			-l for Light Weight Monitor(LWM)
		3. nginx_port and LSA_port must be in range [1-65535] and must be different.
		4.  Alert_Notification options:
			1=Since Last Shutdown
			2=Since Last Clear
			3=Since Last Reboot
			4=Since Newest
			if nginx_port, LSA_port and Alert_Notification is not specified in the command line the default values (Nginx default port 2463, LSA default port 9000 and Alert Notification value 1) will be used.
			
3. The installer provides the user with four types of set-up options.
   1. Gateway - This will install all the features.
   2. StandAlone - This will install components required for Local Server Management.
   3. DirectAgent - This will install components required for Remote Server Management
   4. Light Weight Monitor - This will install Light Weight Monitor program features.
      Refer "Installing the Light Weight Monitor System" section in the user guide for more details.

4. When LWM is Installed, user cannot perform installation of LSA. Needs to do complete un-installation of LWM and then Install LSA.
   When LSA is Installed, user cannot perform installation of LWM. Needs to do complete un-installation of LSA and then Install LWM.

5. Extract the contents of the zip file and install the appropriate package on
  64 bit operating systems.

   LSA_Linux.zip
        x64 -- Contains files for 64 bit platforms

Note: No LSA ICON will be created on Desktop for Ubuntu and openEuler.
==============================
Upgrade/Downgrade Instructions
==============================
1. Downgrade is not supported.
2. User can upgrade to the same mode of installation to which he performed with earlier build.
3. During the upgrade user can move from one mode of installation to another mode of installation.
4. When LWM is Installed, user cannot perform upgrade from LWM to LSA. Needs to do complete un-installation of LWM and then Install LSA
Note: If user has placed/copied any file(s) manually in the <LSA_HOME> directory, those files needs to be manually removed before the un-installation.
	  If the file(s) has not been removed, LSA Upgrade will not be clean.

=================================
Verify RPM signature Instructions
=================================	  
1. Import the public key to RPM DB. Command : rpm --import <public-key.asc>
2. Verify the RPM signature. Command : rpm -Kv <LSA rpm>
3. Install the LSA. If imported public key is for the RPM being installed, No warnings should be shown during installation.

For Ubuntu use below commands:
1. Import the public key to GPG DB. Command Syntax : gpg --import <pubKey.asc>
2. Verify the GPG signature. Command Syntax : gpg --verify <LSIStorageAuthority-xxx.xxx.xxx.xxx-1_amd64.deb.sig> <LSIStorageAuthority-xxx.xxx.xxx.xxx-1_amd64.deb>
3. Install the LSA. If imported public key is for the deb being installed, No warnings should be shown during installation.
 
==============================
Email Security Configuration:
==============================
email_password_mode - Controls content of SMTP MAIL FROM AUTH parameter

1. Secure Mode (0) - Default, Recommended
   a. MAIL FROM AUTH contains: email address only
   b. Password transmitted separately during SMTP authentication
   c. Prevents password from appearing in SMTP server logs
   
2. Full Credentials Mode (1) - NOT RECOMMENDED (Security Risk)
   a. MAIL FROM AUTH contains: email:password
   b. Password may be logged in plain text by SMTP server
   c. Use ONLY if SMTP server explicitly requires this format

Default: 0 (Secure)

When to Use Mode 1:
   Only if email authentication fails with Mode 0 AND your SMTP administrator confirms 
   the server requires credentials in MAIL FROM command. Most modern SMTP servers work with Mode 0.

Troubleshooting: 
   Verify username/password and SMTP settings (host, port, SSL/TLS) before changing to Mode 1.

Note: Both modes perform authentication. Mode 0 keeps password out of logs.

===========================
Un-installation Instructions
===========================
 The product can be uninstalled using the script uninstaller.sh.
 run the script /opt/lsi/LSIStorageAuhority/uninstaller.sh to un-install LSA. This same script can be used to uninstall LSA in Ubuntu OS.

 user may also un-install LSA using the rpm commands.
 Run the command  "rpm -e <rpm_name>" to un-install the RPM's from the target system.
 Example:
 rpm -e LSIStorageAuhority-1.00x.xxx-xxx
 
 For Ubuntu use below commands:
 dpkg -r lsistorageauthority
 dpkg -P lsistorageauthority

============================
LSA & Nginx Service Status:
	1: To Start LSA and Nginx, run "/etc/init.d/LsiSASH start".
	2: To Stop LSA and Nginx, run "/etc/init.d/LsiSASH stop".
	3: To ReStart LSA and Nginx run "/etc/init.d/LsiSASH restart".
    4: To check status of LSA and Nginx, run "/etc/init.d/LsiSASH status".
	
  For Ubuntu use below commands:
	1: To Start LSA and Nginx, run "service LsiSASH start".
	2: To Stop LSA and Nginx, run "service LsiSASH stop".
	3: To ReStart LSA and Nginx run "service LsiSASH restart".
    4: To check status of LSA and Nginx, run "service LsiSASH status".
===========================
