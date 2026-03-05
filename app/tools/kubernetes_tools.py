from kubernetes import client, config
from app.utils.logger import logger
import os

# Initialize kubernetes client once when the module loads
try:
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        logger.info("Loading in-cluster config for Kubernetes")
        config.load_incluster_config()
    else:
        logger.info("Loading kube-config for Kubernetes")
        config.load_kube_config()
    
    v1_client = client.CoreV1Api()
except Exception as e:
    logger.warning(f"Failed to initialize Kubernetes client: {e}")
    v1_client = None

def get_pods(namespace: str) -> list[dict]:
    """
    Get pods in a Kubernetes namespace.
    """
    logger.info(f"Getting pods for namespace: {namespace}")
    
    if not v1_client:
        return [{"error": "Kubernetes client not initialized. Check configuration."}]
        
    try:
        pods = v1_client.list_namespaced_pod(namespace)
        
        pod_list = []
        for pod in pods.items:
            pod_list.append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "restarts": sum([cs.restart_count for cs in pod.status.container_statuses]) if pod.status.container_statuses else 0,
                "created_at": str(pod.metadata.creation_timestamp)
            })
            
        return pod_list
    except Exception as e:
        logger.error(f"Error fetching pods: {e}")
        return [{"error": str(e)}]
