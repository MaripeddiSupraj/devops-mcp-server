from kubernetes import client, config
from devops_mcp.utils.logger import logger
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

def get_kubernetes_pods(namespace: str) -> list[dict]:
    """
    Get pods in a Kubernetes namespace.
    """
    
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

def get_kubernetes_logs(namespace: str, pod_name: str, container_name: str = None) -> dict:
    """
    Get the logs for a specific pod in a namespace.
    Optionally specify a container name if the pod has multiple containers.
    """
    if not v1_client:
        return {"error": "Kubernetes client not initialized."}
        
    try:
        kwargs = {}
        if container_name:
            kwargs['container'] = container_name
            
        logs = v1_client.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=500, **kwargs)
        return {"status": "success", "pod": pod_name, "logs": logs}
    except Exception as e:
        logger.error(f"Error fetching logs for {pod_name}: {e}")
        return {"status": "error", "message": str(e)}

def get_kubernetes_events(namespace: str) -> list[dict]:
    """
    Get the most recent events in a Kubernetes namespace, useful for debugging scheduling or crash loops.
    """
    if not v1_client:
        return [{"error": "Kubernetes client not initialized."}]
        
    try:
        events = v1_client.list_namespaced_event(namespace)
        
        event_list = []
        for event in sorted(events.items, key=lambda x: x.last_timestamp or x.event_time or x.creation_timestamp, reverse=True)[:50]:
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "involved_object": f"{event.involved_object.kind}/{event.involved_object.name}",
                "timestamp": str(event.last_timestamp or event.event_time or event.creation_timestamp)
            })
            
        return event_list
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return [{"error": str(e)}]

def get_kubernetes_deployments(namespace: str) -> list[dict]:
    """
    Get deployments in a Kubernetes namespace, including their readiness state and image versions.
    """
    
    try:
        # Deployments use AppsV1Api
        apps_client = client.AppsV1Api()
        deployments = apps_client.list_namespaced_deployment(namespace)
        
        dep_list = []
        for dep in deployments.items:
            # Extract main container image
            images = [c.image for c in dep.spec.template.spec.containers] if dep.spec.template.spec.containers else []
            
            dep_list.append({
                "name": dep.metadata.name,
                "ready_replicas": dep.status.ready_replicas or 0,
                "desired_replicas": dep.status.replicas or 0,
                "available_replicas": dep.status.available_replicas or 0,
                "images": images,
                "created_at": str(dep.metadata.creation_timestamp)
            })
            
        return dep_list
    except Exception as e:
        logger.error(f"Error fetching deployments: {e}")
        return [{"error": str(e)}]

def get_kubernetes_services(namespace: str) -> list[dict]:
    """
    Get services in a Kubernetes namespace, showing internal IPs and ports.
    """
    if not v1_client:
        return [{"error": "Kubernetes client not initialized."}]
        
    try:
        services = v1_client.list_namespaced_service(namespace)
        
        svc_list = []
        for svc in services.items:
            ports = []
            for p in svc.spec.ports or []:
                port_info = f"{p.port}:{p.target_port}/{p.protocol}"
                if p.node_port:
                    port_info += f" (NodePort: {p.node_port})"
                ports.append(port_info)
                
            svc_list.append({
                "name": svc.metadata.name,
                "type": svc.spec.type,
                "cluster_ip": svc.spec.cluster_ip,
                "ports": ports,
                "selector": svc.spec.selector or {}
            })
            
        return svc_list
    except Exception as e:
        logger.error(f"Error fetching services: {e}")
        return [{"error": str(e)}]

def get_kubernetes_ingresses(namespace: str) -> list[dict]:
    """
    Get ingresses in a Kubernetes namespace, showing external routing and hostnames.
    """
    
    try:
        # Ingresses use NetworkingV1Api
        net_client = client.NetworkingV1Api()
        ingresses = net_client.list_namespaced_ingress(namespace)
        
        ing_list = []
        for ing in ingresses.items:
            hosts = []
            for rule in ing.spec.rules or []:
                hosts.append(rule.host or "*")
                
            ing_list.append({
                "name": ing.metadata.name,
                "ingress_class": ing.spec.ingress_class_name,
                "hosts": hosts,
                "created_at": str(ing.metadata.creation_timestamp)
            })
            
        return ing_list
    except Exception as e:
        logger.error(f"Error fetching ingresses: {e}")
        return [{"error": str(e)}]
