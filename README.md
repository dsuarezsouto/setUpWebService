# Objetivo
Creación de un escenario completo de despliegue de una aplicación fiable y escalable.

# Descripción
En el proyecto se utilizarán los elementos típicos de las arquitecturas	actuales: firewall, balanceador de carga,	servidores front-end corriendo la aplicación, bases de datos y	servidores de almacenamiento.

La aplicación CRM se configurará para que utilice una base de datos PostgreSQL, que correrá	en el servidor de bases	de datos, y para que almacene las imágenes en el cluster de almacenamiento que se creará utilizando el sistema de ficheros distribuido Glusterfs. El balanceador de carga	se ocupará de distribuir la carga entre	los tres servidores que	soportan la aplicación CRM (S1,	S2 y S3) y el cortafuegos de entrada, basado en	el software de Linux FirewallBuilder, se ocupará de filtrar todo el tráfico proveniente de Internet y dejar pasar únicamente el destinado a la aplicación.	
La arquitectura	debe garantizar la escalabilidad de la aplicación, permitiendo ampliar fácilmente el número de	servidores dedicados según crezca el número de usuarios. Por	ello se	parte de un sistema con	un número determinado de servidores, pero se prevé añadir servidores (reales o virtuales) según crezca la	demanda	del servicio.	