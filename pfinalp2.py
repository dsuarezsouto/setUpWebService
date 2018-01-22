import sys
import subprocess
import logging
import argparse
from time import sleep 
from lxml import etree
# DEBUG
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pfinalp2')

# Direcciones IP de los Servidores en la DMZ
IP_SERVIDORES_DMZ = []
# Direcciones IP de los Servidores en la MZ
IP_SERVIDORES_MZ = []
# Direccion IP de la BBDD
IP_BBDD = []
# Direcciones IP de las MV que forman el Gluster
IP_GLUSTER = []
# Direccion IP de la MV GES
IP_GES = []
# Direccion IP de la MZ
IP_MZ = "10.1.4.0/24"

# Funcion privada encargada de leer los diferentes parametros de laas MV definidas en el archivo XML del escenario
def setUp(escenario):

	tree = etree.parse(escenario)
	root = tree.getroot()
	for mv in root.findall("vm"):
		nameMV = mv.get('name')
		logger.debug(nameMV)
		#Las MV de los servidores tienen nombre con formato 'sX', siendo X un numero (e. s1)
		if(nameMV.startswith('s') and nameMV[-1:].isalnum()):
			logger.debug("Servidor "+nameMV[-1:])
			for interface in mv.findall('if'):
				#Guardamos su interfaz en la DMZ
				if(interface.get('net')=='LAN3'):
					ip = interface.find('ipv4').text
					logger.debug(ip)
					IP_SERVIDORES_DMZ.append(ip[0:len(ip)-3])
					logger.debug("IP_DMZ: "+str(IP_SERVIDORES_DMZ))
				#Guardamos su interfaz en la MZ
				if(interface.get('net')=='LAN4'):
					ip = interface.find('ipv4').text
					logger.debug(ip)
					IP_SERVIDORES_MZ.append(ip[0:len(ip)-3])
					logger.debug("IP_MZ: "+str(IP_SERVIDORES_MZ))
		
		#Maquina virtual de la BBDD
		if(nameMV == "bbdd"):
			ip = mv.find('if/ipv4').text
			IP_BBDD.append(ip[0:len(ip)-3])
			logger.debug("IP_BBDD: {ip}".format(ip=IP_BBDD))

		#Las MV virtuales que forman el gluster tienen de nombre 'nasX', siendo X un numero
		if(nameMV.startswith('nas')):
			ip = mv.find('if/ipv4').text
			IP_GLUSTER.append(ip[0:len(ip)-3])
			logger.debug("IP_GLUSTER: {ip}".format(ip=IP_GLUSTER))
		#Maquina vitual de GES
		if(nameMV == "GES"):
			ip = mv.find("if[@id='1']/ipv4").text
			IP_GES.append(ip[0:len(ip)-3])
			logger.debug("IP_GES: {ip}".format(ip=IP_GES))

	


# Funcion privada para configurar los servidores para que arranquen la aplicacion CRM
def setUpServer(i):
	logger.debug("configurando servidor: {numero}".format(numero=i))
	subprocess.call("sudo lxc-attach --clear-env -n s{server} -- apt-get update".format(server=i),shell=True)

	#Copiamos la app CRM
	#ANADIDO DE MANERA PERMANENTE
	#subprocess.call("sudo lxc-attach --clear-env -n s"+str(i)+" -- git clone https://github.com/CORE-UPM/CRM_2017.git",shell=True)
	#subprocess.call("sudo lxc-attach --clear-env -n s"+str(i)+" -- bash -c 'curl -sL https://deb.nodesource.com/setup_7.x | bash -'",shell=True)
	#subprocess.call("sudo lxc-attach --clear-env -n s"+str(i)+" -- apt-get install nodejs -y",shell=True)
	#subprocess.call("sudo lxc-attach --clear-env -n s"+str(i)+" -- bash -c 'cd CRM_2017 && npm install -y'",shell=True)

	#Configuracion del montaje de los servidores con el cluster de almacenamiento para la sincronicacion de las imagenes de la plicacion
	subprocess.call("sudo lxc-attach --clear-env -n s{server} -- mkdir /root/CRM_2017/public/uploads".format(server=i),shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n s{server} -- mount -t glusterfs nas1:/nas /root/CRM_2017/public/uploads".format(server=i,ipNas1=IP_GLUSTER[0]),shell=True)	
	#subprocess.call("sudo lxc-attach --clear-env -n s{server} -- mkdir /mnt/nas".format(server=i),shell=True)
	#subprocess.call("sudo lxc-attach --clear-env -n s{server} -- mount -t glusterfs nas1:/nas /mnt/nas".format(server=i),shell=True)
	#subprocess.call("sudo lxc-attach --clear-env -n s{server} -- ln -s /mnt/nas /root/CRM_2017/public/uploads".format(server=i),shell=True)
	
	subprocess.call("sudo lxc-attach --clear-env -n s{server} -- bash -c 'cd /root/CRM_2017 && npm install forever'".format(server=i),shell=True)

	
	if(str(i)=="1"):
		subprocess.call("sudo lxc-attach --clear-env -n s{server} --set-var 'DATABASE_URL=postgres://crm:xxxx@{ipBBDD}:5432/crm' -- bash -c 'cd /root/CRM_2017 && npm run-script migrate_local'".format(server=i,ipBBDD=IP_BBDD[0]),shell=True)
		subprocess.call("sudo lxc-attach --clear-env -n s{server} --set-var 'DATABASE_URL=postgres://crm:xxxx@{ipBBDD}:5432/crm' -- bash -c 'cd /root/CRM_2017 && npm run-script seed_local'".format(server=i,ipBBDD=IP_BBDD[0]),shell=True)

	subprocess.call("sudo lxc-attach --clear-env -n s{server} --set-var 'DATABASE_URL=postgres://crm:xxxx@{ipBBDD}:5432/crm' -- /root/CRM_2017/node_modules/forever/bin/forever start /root/CRM_2017/bin/www".format(server=i,ipBBDD=IP_BBDD[0]),shell=True)
	
	

# Funcion privada que configura una BBDD con PostgreSQL
def setUpBBDD():

	subprocess.call("sudo lxc-attach --clear-env -n bbdd -- apt update", shell=True)
	#Anadido de forma permanente
	#subprocess.call("sudo lxc-attach --clear-env -n bbdd -- apt -y install postgresql", shell=True)

	cmd4 = "sudo lxc-attach --clear-env -n bbdd -- bash -c \" echo 'listen_addresses = '\\\"'{ipBBDD}'\\\"'' >> /etc/postgresql/9.6/main/postgresql.conf \" ".format(ipBBDD=IP_BBDD[0])
	subprocess.call(cmd4, shell=True)
	logger.debug("IP anadida")
	subprocess.call('''sudo lxc-attach --clear-env -n bbdd -- bash -c "echo 'host all all {ipMZ} trust' >> /etc/postgresql/9.6/main/pg_hba.conf" '''.format(ipMZ=IP_MZ), shell=True)
	logger.debug("Host all all anadido")

	cmd1 = "sudo lxc-attach --clear-env -n bbdd -- bash -c \" echo 'CREATE USER crm with PASSWORD '\\\"'xxxx'\\\"';' | sudo -u postgres psql \" "
	cmd2 = "sudo lxc-attach --clear-env -n bbdd -- bash -c \" echo 'CREATE DATABASE crm;' | sudo -u postgres psql \" "
	cmd3 = "sudo lxc-attach --clear-env -n bbdd -- bash -c \" echo 'GRANT ALL PRIVILEGES ON DATABASE crm to crm;' | sudo -u postgres psql \" "

	subprocess.call(cmd1, shell=True)
	logger.debug("Usuario creado")
	subprocess.call(cmd2, shell=True)
	logger.debug("Database creada")
	subprocess.call(cmd3, shell=True)
	logger.debug("Privilegios dados")
	subprocess.call("sudo lxc-attach --clear-env -n bbdd -- systemctl restart postgresql", shell=True)
	logger.debug("Reiniciado")
	
# Funcion privada que configura un Gluster con el programa GlusterFS
def setUpCluster():
	logger.debug("Iniciando Cluster")
	nServidoresGluster = len(IP_GLUSTER)
	# Creamos el comando para crear el volumen llamado 'nas'
	cmd = "gluster volume create nas replica {nServidoresGluster}".format(nServidoresGluster=nServidoresGluster)
	#Modificamos los archivos /etc/hosts
	for i in range(1,nServidoresGluster+1):
		#subprocess.call("sudo lxc-attach -n nas{i} -- sed -i.bak 's|127.0.1.1  nas{i}|127.0.1.1  nas{i} \n10.1.4.21 nas1 \n10.1.4.22 nas2 \n10.1.4.23 nas3|g' /etc/hosts".format(i=i),shell=True)
		subprocess.call("sudo lxc-attach -n nas{i} -- bash -c \" echo '10.1.4.21 nas1' >> /etc/hosts \" ".format(i=i),shell=True)
		subprocess.call("sudo lxc-attach -n nas{i} -- bash -c \" echo '10.1.4.22 nas2' >> /etc/hosts \" ".format(i=i),shell=True)
		subprocess.call("sudo lxc-attach -n nas{i} -- bash -c \" echo '10.1.4.23 nas3' >> /etc/hosts \" ".format(i=i),shell=True)
		#Anadimos un servidor al cmd
		cmd += " nas{i}:/nas/".format(i=i)
		if(i != 1):
			#Anadimos los nas para realizar mas adelante el gluster
			subprocess.call("sudo lxc-attach --clear-env -n nas1 -- gluster peer probe nas{i}".format(i=i),shell=True)
			sleep(5)


	cmd += " force"
	
	#Realizamos un gluster con replica con los 3 nas y lo arrancamos
	subprocess.call("sudo lxc-attach --clear-env -n nas1 -- {comando}".format(comando=cmd), shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nas1 -- gluster volume start nas", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nas1 -- gluster volume info",shell=True)

	
	for i in range(1,nServidoresGluster+1):
		#Cambiamos el valor del timeout para agilizar en caso de caida de algun servidor
		logger.debug("Modificando servidor: {nas}".format(nas=i))
		subprocess.call("sudo lxc-attach --clear-env -n nas{nas} -- gluster volume set nas network.ping-timeout 5".format(nas=i), shell=True)

#Funcion privada que configura el FW a traves de un archivo creado previamente con el programa fwbuilder
def setUpFW():
	subprocess.call("sudo cp ./fw.fw /var/lib/lxc/fw/rootfs/root/",shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n fw -- chmod +x /root/fw.fw",shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n fw -- ./root/fw.fw",shell=True)

# Funcion privada que configura el LB con balanceo de carga del tipo round robin
def setUpLB():

	cmd = "sudo lxc-attach -n lb -- xr -dr --server tcp:0:80"
	for ipServer in IP_SERVIDORES_DMZ:
		cmd+= " --backend {ipServer}:3000".format(ipServer=ipServer)
	cmd+= " --web-interface 0:8001 &"
	logger.debug("LB: {cmd}".format(cmd=cmd))
	subprocess.call(cmd, shell=True)
	
# Funcion privada que anade un nuevo servidor al escenario a traves de su archivo XML
def addServer(fileServer):
	subprocess.call("sudo vnx -f {file} --create".format(file=fileServer),shell=True)
	tree = etree.parse(fileServer)
	root = tree.getroot()
	mv = root.find('vm')

	nameServer = mv.get('name')
	for interface in mv.findall('if'):
		#Guardamos su interfaz en la DMZ
		if(interface.get('net')=='LAN3'):
			ip = interface.find('ipv4').text
			logger.debug(ip)
			IP_SERVIDORES_DMZ.append(ip[0:len(ip)-3])
			logger.debug("IP_DMZ: "+str(IP_SERVIDORES_DMZ))
		#Guardamos su interfaz en la MZ
		if(interface.get('net')=='LAN4'):
			ip = interface.find('ipv4').text
			logger.debug(ip)
			IP_SERVIDORES_MZ.append(ip[0:len(ip)-3])
			logger.debug("IP_MZ: "+str(IP_SERVIDORES_MZ))

	logger.debug("nameServer: {name}".format(name=nameServer))
	logger.debug("IP_MZ:{ips}".format(ips=IP_SERVIDORES_MZ))
	logger.debug("Numero de servidor: {numero}".format(numero=nameServer[len(nameServer)-1]))

	subprocess.call("sudo lxc-attach --clear-env -n {nameServer} -- sudo sed -i.bak -r 's/(archive|security).ubuntu.com/old-releases.ubuntu.com/g' /etc/apt/sources.list".format(nameServer=nameServer),shell=True)
	setUpServer(4)
	#Metemos nagios
	cmd_hosts4 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host  s4' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name s4' '\n'  'alias s4'  '\n'  'address 10.1.3.14' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_hosts4,shell=True)
	cmd_service1s4 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de s4' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name s4' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service2s4 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name s4' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_service1s4,shell=True)
	subprocess.call(cmd_service2s4,shell=True)
	#Reiniciamos nagios
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart apache2.service", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart nagios.service", shell=True)

	#Reseteamos el LB
	subprocess.call("sudo lxc-attach -n lb -- killall xr", shell=True)
	setUpLB()

# Funcion privada que borra un servidor del escenario a traves de su archivo XML
def deleteServer(fileServer):
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- rm -r /usr/local/nagios/etc/objects/escenario.cfg", shell=True)
	subprocess.call("sudo vnx -f {file} --destroy".format(file=fileServer),shell=True)
	subprocess.call("sudo lxc-attach -n lb -- killall xr", shell=True)
	setUpLB()

# Funcion privada que anade un nuevo servidor de gestion al escenario
def setUpGES():
	#Generamos el par de claves RSA
	subprocess.call("sudo ssh-keygen -y -t rsa -N '' -f /home/cdps/.ssh/id_rsa",shell=True)
	logger.debug("CREADA LA CLAVE RSA")
	#Copiamos la clave publica al servidor GES
	subprocess.call("sudo ssh-copy-id -i /home/cdps/.ssh/id_rsa.pub root@GES",shell=True)

	#Modifico el archivo ssh_config para bloquear el accceso por usuario y contrasena
	subprocess.call("sudo lxc-attach -n GES -- sed -i.bak 's|#PasswordAuthentication yes|PasswordAuthentication no|g' /etc/ssh/sshd_config",shell=True)
	subprocess.call("sudo lxc-attach -n GES -- service ssh restart",shell=True)

# Funcion privada que anade un nuevo servidor de monitorizacion al escenario
def setUpNagios():
	#Actualizo la maquina Nagios para que tenga los paquetes necesarios para Nagios
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo apt-get update ", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo apt-get install -y autoconf gcc libc6 make wget unzip apache2 php libapache2-mod-php7.0 libgd2-xpm-dev ", shell=True)
	#Descargamos Nagios y descomprimimos

	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp && wget -O nagioscore.tar.gz https://github.com/NagiosEnterprises/nagioscore/archive/nagios-4.3.4.tar.gz'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp && tar xzf nagioscore.tar.gz'", shell=True)

	#Instalamos y configuramos Nagios, ademas de anadir el superusuario nagiosadmin con password xxxx
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo ./configure --with-httpd-conf=/etc/apache2/sites-enabled'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo make all'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && useradd nagios '", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo usermod -a -G nagios www-data'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo make install'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo make install-init'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo update-rc.d nagios defaults'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo make install-commandmode'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo make install-config'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo make install-webconf' ", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo a2enmod rewrite'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo a2enmod cgi'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo systemctl restart apache2.service'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagioscore-nagios-4.3.4/ && sudo systemctl start nagios.service'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo apt-get install -y autoconf gcc libc6 libmcrypt-dev make libssl-dev wget bc gawk dc build-essential snmp libnet-snmp-perl gettext", shell=True)

	#Descargamos plugins de Nagios
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp && wget --no-check-certificate -O nagios-plugins.tar.gz https://github.com/nagios-plugins/nagios-plugins/archive/release-2.2.1.tar.gz'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp && tar zxf nagios-plugins.tar.gz'", shell=True)

	#Configuramos e instalamos dichos plugins
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagios-plugins-release-2.2.1/ && sudo ./tools/setup'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagios-plugins-release-2.2.1/ && sudo ./configure'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagios-plugins-release-2.2.1/ && sudo make'", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'cd /tmp/nagios-plugins-release-2.2.1/ && sudo make install'", shell=True)

# Funcion privada que configura el servidor Nagios para monitorizar las MV
def addNagios():

	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'sudo systemctl start nagios.service'", shell=True)

	#Anadimos el usuario en la maquina Nagios solamente
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- bash -c 'sudo htpasswd -c -b /usr/local/nagios/etc/htpasswd.users nagiosadmin xxxx'", shell=True)


	#Anadimos bbdd
	cmd_hostbbdd = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host bbdd ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name bbdd' '\n'  'alias bbdd'  '\n'  'address 10.1.4.31' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_hostbbdd,shell=True)
	cmd_service1bbdd = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de bbdd ' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name bbdd' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service2bbdd = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name bbdd' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_service1bbdd,shell=True)
	subprocess.call(cmd_service2bbdd,shell=True)

	#Anadimos los servidores
	for i in range(1,4):
		cmd_hosts = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host  s"+str(i)+"' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name s"+str(i)+"' '\n'  'alias s"+str(i)+"'  '\n'  'address 10.1.3.1"+str(i)+"' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
		subprocess.call(cmd_hosts,shell=True)
		cmd_service1s = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de s"+str(i)+"' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name s"+str(i)+"' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
		cmd_service2s = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name s"+str(i)+"' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
		subprocess.call(cmd_service1s,shell=True)
		subprocess.call(cmd_service2s,shell=True)

	#Anadimos el Cluster
	cmd_hostnas1 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host nas1 ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name nas1' '\n'  'alias nas1'  '\n'  'address 10.1.4.21' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_hostnas2 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host nas2 ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name nas2' '\n'  'alias nas2'  '\n'  'address 10.1.4.22' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_hostnas3 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host nas3 ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name nas3' '\n'  'alias nas3'  '\n'  'address 10.1.4.23' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_hostnas1,shell=True)
	subprocess.call(cmd_hostnas2,shell=True)
	subprocess.call(cmd_hostnas3,shell=True)
	cmd_nas1service1 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de nas1 ' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name nas1' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_nas1service2 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name nas1' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_nas1service1,shell=True)
	subprocess.call(cmd_nas1service2,shell=True)
	cmd_nas2service1 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de nas2 ' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name nas2' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_nas2service2 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name nas2' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_nas2service1,shell=True)
	subprocess.call(cmd_nas2service2,shell=True)
	cmd_nas3service1 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de nas3 ' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name nas3' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_nas3service2 = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name nas3' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_nas3service1,shell=True)
	subprocess.call(cmd_nas3service2,shell=True)			

	#Anadimos el FW
	cmd_hostfw = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host fw ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name fw' '\n'  'alias fw'  '\n'  'address 10.1.1.1' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_hostfw,shell=True)
	cmd_service1fw = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de fw ' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name fw' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service2fw = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name fw' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_service1fw,shell=True)
	subprocess.call(cmd_service2fw,shell=True)

	#Anadimos el LB
	cmd_hostlb = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host lb ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name lb' '\n'  'alias lb'  '\n'  'address 10.1.2.2' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_hostlb,shell=True)
	cmd_service1lb = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de lb' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name lb' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service2lb = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name lb' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service3lb = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name lb' '\n'  'service_description HTTP'  '\n'  'check_command check_http' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_service1lb,shell=True)
	subprocess.call(cmd_service2lb,shell=True)
	subprocess.call(cmd_service3lb,shell=True)

	#Anadimos el GES
	cmd_hostges = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Host ges ' '\n' 'define host{'  '\n'  'use linux-server' '\n''host_name ges' '\n'  'alias ges'  '\n'  'address 10.1.3.20' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_hostges,shell=True)
	cmd_service1ges = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo '#Servicios de ges ' '\n' 'define service{'  '\n'  'use local-service' '\n''host_name ges' '\n'  'service_description Root Partition'  '\n'  'check_command check_local_disk!20%!10%!/' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service2ges = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name ges' '\n'  'service_description Current Users'  '\n'  'check_command check_local_users!20!50' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	cmd_service3ges = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'define service{'  '\n'  'use local-service' '\n''host_name ges' '\n'  'service_description SSH'  '\n'  'check_command check_ssh' '\n''}' >> /usr/local/nagios/etc/objects/escenario.cfg \" "
	subprocess.call(cmd_service1ges,shell=True)
	subprocess.call(cmd_service2ges,shell=True)
	subprocess.call(cmd_service3ges,shell=True)

	#Reiniciamos nagios para aplicar los cambios
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart apache2.service", shell=True)
	subprocess.call("sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart nagios.service", shell=True)
	

if __name__ == '__main__':	

	parser = argparse.ArgumentParser()
	parser.add_argument("scenarioFile",help="Archivo XML con la informacion del escenario a crear")
	parser.add_argument("--create",action="store_true",help="Crea el escenario correspondiente al archivo xml pasado como parametro")
	parser.add_argument("--shutdown",action="store_true",help="Detiene el escenario")
	parser.add_argument("--destroy",action="store_true",help="Destruye el escenario")
	parser.add_argument("--addServer",nargs=1,help="Anade un servidor al escenario correspondiente al archivo XML pasado como parametro")
	parser.add_argument("--deleteServer",nargs=1,help="Borra un servidor al escenario correspondiente al archivo XML pasado como parametro")
	parser.add_argument("--addNagios",action="store_true",help="Anade el fichero de configuracion de Nagios")


	args = parser.parse_args()
	if args.create:
		subprocess.call("sudo vnx -f {file} --create".format(file=args.scenarioFile),shell=True)
		sys.exit()
	if args.shutdown:
		subprocess.call("sudo vnx -f {file} --shutdown".format(file=args.scenarioFile),shell=True)
		sys.exit()
	if args.destroy:
		subprocess.call("sudo vnx -f {file} --destroy".format(file=args.scenarioFile),shell=True)
		sys.exit()
	if args.addServer:
		setUp(args.scenarioFile)
		logger.debug(args.addServer)
		addServer(args.addServer[0])
		sys.exit()
	if args.deleteServer:
		setUp(args.scenarioFile)
		deleteServer(args.deleteServer[0])
		addNagios()
		sys.exit()
	if args.addNagios:
		#Anadimos la ruta donde se configuran las maquinas y sus servicios
		cmd_conf = "sudo lxc-attach --clear-env -n nagios -- bash -c \"echo 'cfg_file=/usr/local/nagios/etc/objects/escenario.cfg' >> /usr/local/nagios/etc/nagios.cfg \" "
		subprocess.call(cmd_conf,shell=True)
		setUp(args.scenarioFile)
		addNagios()
		sys.exit()	

	logger.debug(args.scenarioFile)
	setUp(args.scenarioFile)
	logger.debug("IP_DMZ: "+str(IP_SERVIDORES_DMZ))
	logger.debug("IP_BBDD: "+str(IP_BBDD))


	setUpNagios()

	setUpBBDD()

	setUpCluster()

	setUpGES()

	logger.debug("Servidores a iniciar: "+str(len(IP_SERVIDORES_DMZ)))
	for i in range(1,len(IP_SERVIDORES_DMZ)+1):
		logger.debug("Iniciando servidor: "+str(i))
		setUpServer(i)
		
	setUpLB()
	setUpFW()
	
