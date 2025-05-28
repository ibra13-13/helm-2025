from kubernetes import client, config, watch


# Load Kubernetes Config
config.load_kube_config()


# Initialize API clients
api = client.CustomObjectsApi()
apps_v1 = client.AppsV1Api()
core_v1 = client.CoreV1Api()


namespace = "default"


# Function to create a Secret for database credentials
def create_secret(namespace, db_name):
   secret_name = f"{db_name}-credentials"
   secret = client.V1Secret(
       metadata=client.V1ObjectMeta(name=secret_name),
       string_data={
           "MYSQL_ROOT_PASSWORD": "password",
           "MYSQL_USER": "admin",
           "MYSQL_PASSWORD": "admin123",
           "MYSQL_DATABASE": "mydatabase"
       }
   )
   try:
       core_v1.create_namespaced_secret(namespace=namespace, body=secret)
       print(f"✅ Secret {secret_name} created.")
   except Exception as e:
       print(f"⚠️ Secret {secret_name} already exists or failed: {e}")


# Function to create a Persistent Volume Claim (PVC)
def create_pvc(namespace, db_name):
   pvc_name = f"{db_name}-pvc"
   pvc = client.V1PersistentVolumeClaim(
       metadata=client.V1ObjectMeta(name=pvc_name),
       spec=client.V1PersistentVolumeClaimSpec(
           access_modes=["ReadWriteOnce"],
           resources=client.V1ResourceRequirements(requests={"storage": "10Gi"})
       )
   )
   try:
       core_v1.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
       print(f"✅ PVC {pvc_name} created.")
   except Exception as e:
       print(f"⚠️ PVC {pvc_name} already exists or failed: {e}")


# Function to create a Deployment for MySQL or PostgreSQL
def create_deployment(namespace, db_name, db_engine, replicas):
   deployment = client.V1Deployment(
       metadata=client.V1ObjectMeta(name=db_name),
       spec=client.V1DeploymentSpec(
           replicas=replicas,
           selector={"matchLabels": {"app": db_name}},
           template=client.V1PodTemplateSpec(
               metadata=client.V1ObjectMeta(labels={"app": db_name}),
               spec=client.V1PodSpec(
                   containers=[
                       client.V1Container(
                           name=db_name,
                           image="mysql:8.0" if db_engine == "mysql" else "postgres:latest",
                           env=[
                               client.V1EnvVar(
                                   name="MYSQL_ROOT_PASSWORD",
                                   value_from=client.V1EnvVarSource(
                                       secret_key_ref=client.V1SecretKeySelector(
                                           name=f"{db_name}-credentials", key="MYSQL_ROOT_PASSWORD"
                                       )
                                   ),
                               ),
                               client.V1EnvVar(
                                   name="MYSQL_USER",
                                   value_from=client.V1EnvVarSource(
                                       secret_key_ref=client.V1SecretKeySelector(
                                           name=f"{db_name}-credentials", key="MYSQL_USER"
                                       )
                                   ),
                               ),
                               client.V1EnvVar(
                                   name="MYSQL_PASSWORD",
                                   value_from=client.V1EnvVarSource(
                                       secret_key_ref=client.V1SecretKeySelector(
                                           name=f"{db_name}-credentials", key="MYSQL_PASSWORD"
                                       )
                                   ),
                               ),
                               client.V1EnvVar(
                                   name="MYSQL_DATABASE",
                                   value_from=client.V1EnvVarSource(
                                       secret_key_ref=client.V1SecretKeySelector(
                                           name=f"{db_name}-credentials", key="MYSQL_DATABASE"
                                       )
                                   ),
                               ),
                           ],
                           volume_mounts=[client.V1VolumeMount(mount_path="/var/lib/mysql", name="mysql-storage")],
                       )
                   ],
                   volumes=[
                       client.V1Volume(
                           name="mysql-storage",
                           persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                               claim_name=f"{db_name}-pvc"
                           )
                       )
                   ]
               )
           )
       )
   )
   try:
       apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
       print(f"✅ Deployment {db_name} created.")
   except Exception as e:
       print(f"⚠️ Deployment {db_name} already exists or failed: {e}")


# Function to create a Service for the database
def create_service(namespace, db_name):
   service_name = f"{db_name}-service"
   service = client.V1Service(
       metadata=client.V1ObjectMeta(name=service_name),
       spec=client.V1ServiceSpec(
           selector={"app": db_name},
           ports=[client.V1ServicePort(port=3306, target_port=3306)]
       )
   )
   try:
       core_v1.create_namespaced_service(namespace=namespace, body=service)
       print(f"✅ Service {service_name} created.")
   except Exception as e:
       print(f"⚠️ Service {service_name} already exists or failed: {e}")


# Watch for Database resource changes
w = watch.Watch()
print("🔍 Watching for new Database resources...")


for event in w.stream(api.list_namespaced_custom_object, group="myorg.com", version="v1", namespace="default", plural="databases"):
   db = event['object']
   db_name = db['metadata']['name']
   db_engine = db['spec']['engine']
   replicas = db['spec']['replicas']


   print(f"📌 Detected new Database: {db_name} ({db_engine}) with {replicas} replicas.")
  
   create_secret(namespace, db_name)
   create_pvc(namespace, db_name)
   create_deployment(namespace, db_name, db_engine, replicas)
   create_service(namespace, db_name)
  
   print(f"🎉 All resources created successfully for {db_name}!\n")