# Goal
Creation of a complete scenario for the deployment of a reliable and scalable application.
# Description
The project will use the typical elements of current architectures: firewall, load balancer, front-end servers running the application, databases and storage servers.

The CRM application will be configured to use a PostgreSQL database, which will run on the database server, and to store the images in the storage cluster that will be created using the Glusterfs distributed file system. The load balancer will distribute the load among the three servers that support the CRM application (S1, S2 and S3) and the entrance firewall, based on the Linux FirewallBuilder software, will take care of filtering all the traffic coming from the Internet and let only the traffic destined to the application pass. The architecture must guarantee the scalability of the application, allowing the number of dedicated servers to be easily expanded as the number of users grows. For this reason, we start from a system with a certain number of servers, but we plan to add servers (real or virtual) as the demand for the service grows.
