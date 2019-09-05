#!/usr/bin/python
import os
import re
import sys
from subprocess import Popen,PIPE

def getsplunk_std():
    spkpid=Popen('pidof splunkd', shell=True, stdout=PIPE).communicate()[0].strip().split()
    if os.path.exists('/opt/splunkforwarder/var/run/splunk/splunkd.pid') and len(spkpid) > 0:
        pi=Popen(' cat /opt/splunkforwarder/var/run/splunk/splunkd.pid', shell=True, stdout=PIPE).communicate()[0].strip().split()
        for pid in spkpid:
            if pid in pi:
               spk_std = True
               break
            else:
               spk_std = False
    else:
        spk_std = False
    return spk_std


def spk_home():
    spk_home = ''
    for root,dirs,files in os.walk('/'):
        if 'splunkd.pid' in files:
            file = os.path.join(root, 'splunkd.pid')
            spk_home = re.sub(r'var.*','',file)
            break
    return spk_home


def spk_apps_backup(splunk_home):
    apss = ''
    bkp_stat = True
    spk_apps = os.path.join(splunk_home + 'etc/apps/')
    if os.path.exists(spk_apps):
        apps = os.listdir(spk_apps)
        stat = os.system("cp -pr %s  %s_bkp"% (spk_apps , spk_apps[:-1]))
        if stat != 0:
            bkp_stat = False
        else:
            bkp_stat = True
    else:
        apps = []
        bkp_stat = False
    return apps,bkp_stat

def copy_old_apps(spk_apps,spk_apps_std):
    compare = ['introspection_generator_addon','learned','search','splunk_httpinput','SplunkUniversalForwarder']
    for apps_folder in os.listdir(spk_apps):
        if apps_folder not in compare:
            print os.path.join(spk_apps + apps_folder)
            os.system("cp -pr %s  %s" %(os.path.join(spk_apps + apps_folder),spk_apps_std))
        else:
            pass

def set_depconf(dep_conf,spk_dep_std):
    fd = open(dep_conf)
    for line in fd:
        if re.search(r'targetUri',line):
            ds = line.split('=')[1].split(':')[0].strip()
            dep_update = Popen('/opt/splunkforwarder/bin/splunk set deploy-poll %s:8089 -auth admin:changeme' %ds, shell=True, stdout=PIPE)
            dep_update.wait()
            if dep_update.poll() !=0:
                return False
            else:
                return True

def create_ignoreapps(spk_apps):
    os.system('mkdir -p %sIgnoreOlderData/local'  %(spk_apps))
    ignore_file = os.path.join(spk_apps,'IgnoreOlderData/local/inputs.conf')
    fh = open(ignore_file,'w')
    fh.write("[default]\nignoreOlderThan = 30m\n" )
    fh.close()


def spk_install(rpm_path):
    stat_inst = os.system("rpm -i %s &>/dev/null" %(rpm_path) )
    if stat_inst !=0:
        return False
    else:
        license_stat = Popen('/opt/splunkforwarder/bin/splunk start --accept-license --answer-yes', shell = True , stdout=PIPE)
        license_stat.wait()
        Popen('/opt/splunkforwarder/bin/splunk enable boot-start', shell = True , stdout=PIPE)
        return True

def main():
    spk_apps_std = '/opt/splunkforwarder/etc/apps/'
    spk_dep_std = '/opt/splunkforwarder/etc/system/local/deploymentclient.conf'
    if getsplunk_std():
            print "Splunk Running from Std Location"
    else:
        splunkhome = spk_home()
        if splunkhome != '':
            spk_apps = os.path.join(splunkhome + 'etc/apps/')
            dep_conf = os.path.join(splunkhome + 'etc/system/local/deploymentclient.conf')
            spk_bin = os.path.join(splunkhome +'bin/splunk')
            splunkhome_owner = os.stat(splunkhome).st_uid
            splunkhome_group = os.stat(splunkhome).st_gid
            apps,bkp_stat = spk_apps_backup(splunkhome)
            if bkp_stat:
                stop_spk = Popen('%s stop' % (spk_bin),shell = True , stdout = PIPE)
                stop_spk.wait()
                path = '/root/splunkforwarder-7.0.4-68ba48f99743-linux-2.6-x86_64.rpm'
                if spk_install(path):
                    create_ignoreapps(spk_apps)
                    copy_old_apps(spk_apps,spk_apps_std)
                    set_depconf(dep_conf,spk_dep_std)
                    os.chown(spk_apps_std,splunkhome_owner,splunkhome_group)
                else:
                    print "Unable to Install RPM "
            else:
                print "Failed to Take Backup"
        else:
            print "Unable to Find Splunk_Home"
            sys.exit()


main()


