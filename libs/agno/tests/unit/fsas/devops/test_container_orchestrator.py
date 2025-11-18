"""
Unit tests for Container Orchestrator FSA

This test suite provides comprehensive coverage of container lifecycle management,
Kubernetes orchestration, auto-scaling, service mesh integration, and advanced
container deployment capabilities.

Test coverage includes:
- Container creation, start, stop, restart, removal
- Kubernetes pod, deployment, service management
- Network and volume configuration
- Health monitoring and auto-healing
- Resource allocation
- Image management
- Docker Compose orchestration
- Service discovery and load balancing
- Auto-scaling (HPA and VPA)
- Rolling updates and rollbacks
- ConfigMap and Secret management
- StatefulSet, DaemonSet, Job, CronJob
- Network policies
- Service mesh integration
- Registry management
- Multi-container orchestration
- Edge cases and error handling

Author: Agno AI
Version: 1.0.0
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json

from agno.fsas.devops.container_orchestrator_fsa import (
    ContainerOrchestratorFSA,
    ContainerState,
    KubernetesResourceType,
    NetworkMode,
    ServiceMeshType,
    ContainerMetrics,
    HealthCheckConfig,
    ResourceLimits
)


@pytest.fixture
def orchestrator():
    """Create Container Orchestrator FSA instance for testing"""
    return ContainerOrchestratorFSA(
        docker_host="unix:///var/run/docker.sock",
        kubernetes_config=None,
        default_namespace="default",
        enable_monitoring=True,
        enable_auto_healing=True,
        monitoring_interval=30
    )


@pytest.fixture
def sample_container_config():
    """Sample container configuration"""
    return {
        "name": "test-container",
        "command": ["python", "app.py"],
        "environment": {"ENV": "test"},
        "ports": {"80/tcp": 8080},
        "volumes": {"/data": "/app/data"},
        "network_mode": "bridge",
        "restart_policy": "always"
    }


@pytest.fixture
def sample_pod_spec():
    """Sample Kubernetes pod specification"""
    return {
        "metadata": {
            "name": "test-pod",
            "labels": {"app": "test"}
        },
        "spec": {
            "containers": [
                {
                    "name": "nginx",
                    "image": "nginx:latest",
                    "ports": [{"containerPort": 80}]
                }
            ]
        }
    }


@pytest.fixture
def sample_deployment_spec():
    """Sample Kubernetes deployment specification"""
    return {
        "metadata": {
            "name": "test-deployment",
            "labels": {"app": "test"}
        },
        "spec": {
            "replicas": 3,
            "selector": {"matchLabels": {"app": "test"}},
            "template": {
                "metadata": {"labels": {"app": "test"}},
                "spec": {
                    "containers": [
                        {
                            "name": "nginx",
                            "image": "nginx:latest",
                            "ports": [{"containerPort": 80}]
                        }
                    ]
                }
            }
        }
    }


# Test 1: Initialization
def test_orchestrator_initialization(orchestrator):
    """Test Container Orchestrator FSA initialization"""
    assert orchestrator is not None
    assert orchestrator.docker_host == "unix:///var/run/docker.sock"
    assert orchestrator.default_namespace == "default"
    assert orchestrator.enable_monitoring is True
    assert orchestrator.enable_auto_healing is True
    assert len(orchestrator.containers) == 0
    assert len(orchestrator.deployments) == 0


# Test 2: Container creation
def test_create_container(orchestrator, sample_container_config):
    """Test container creation"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)

    assert container_id is not None
    assert len(container_id) == 64
    assert container_id in orchestrator.containers
    assert orchestrator.containers[container_id]["name"] == "test-container"
    assert orchestrator.containers[container_id]["image"] == "nginx:latest"
    assert orchestrator.containers[container_id]["state"] == ContainerState.CREATED.value


# Test 3: Container start
def test_start_container(orchestrator, sample_container_config):
    """Test starting a container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    result = orchestrator.start_container(container_id)

    assert result["success"] is True
    assert result["container_id"] == container_id
    assert result["state"] == ContainerState.RUNNING.value
    assert orchestrator.containers[container_id]["state"] == ContainerState.RUNNING.value


# Test 4: Container stop
def test_stop_container(orchestrator, sample_container_config):
    """Test stopping a container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)
    result = orchestrator.stop_container(container_id, timeout=10)

    assert result["success"] is True
    assert result["container_id"] == container_id
    assert result["state"] == ContainerState.EXITED.value
    assert orchestrator.containers[container_id]["state"] == ContainerState.EXITED.value


# Test 5: Container restart
def test_restart_container(orchestrator, sample_container_config):
    """Test restarting a container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)
    result = orchestrator.restart_container(container_id)

    assert result["success"] is True
    assert result["container_id"] == container_id
    assert result["state"] == ContainerState.RUNNING.value


# Test 6: Container removal
def test_remove_container(orchestrator, sample_container_config):
    """Test removing a container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)
    result = orchestrator.remove_container(container_id, force=True)

    assert result["success"] is True
    assert result["removed"] is True
    assert container_id not in orchestrator.containers


# Test 7: Remove running container without force
def test_remove_running_container_without_force(orchestrator, sample_container_config):
    """Test removing running container without force flag"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    with pytest.raises(ValueError, match="Container is running"):
        orchestrator.remove_container(container_id, force=False)


# Test 8: Kubernetes pod creation
def test_orchestrate_kubernetes_pod(orchestrator, sample_pod_spec):
    """Test Kubernetes pod orchestration"""
    result = orchestrator.orchestrate_kubernetes_pod(sample_pod_spec, "default")

    assert result["success"] is True
    assert result["pod_name"] == "test-pod"
    assert result["namespace"] == "default"
    assert result["state"] == "Running"


# Test 9: Kubernetes deployment creation
def test_create_kubernetes_deployment(orchestrator, sample_deployment_spec):
    """Test Kubernetes deployment creation"""
    result = orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    assert result["success"] is True
    assert result["deployment_name"] == "test-deployment"
    assert result["namespace"] == "default"
    assert result["replicas"] == 3
    assert result["state"] == "Available"


# Test 10: Container network configuration
def test_configure_container_network(orchestrator, sample_container_config):
    """Test container network configuration"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)

    network_config = {
        "mode": "bridge",
        "network_name": "test-network",
        "ip_address": "172.17.0.2",
        "aliases": ["nginx-alias"],
        "dns_servers": ["8.8.8.8", "8.8.4.4"]
    }

    result = orchestrator.configure_container_network(container_id, network_config)

    assert result["success"] is True
    assert result["network_mode"] == "bridge"
    assert result["ip_address"] == "172.17.0.2"


# Test 11: Volume attachment
def test_attach_volume(orchestrator, sample_container_config):
    """Test attaching volume to container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)

    volume_config = {
        "name": "test-volume",
        "mount_path": "/data",
        "read_only": False,
        "driver": "local"
    }

    result = orchestrator.attach_volume(container_id, volume_config)

    assert result["success"] is True
    assert result["volume_name"] == "test-volume"
    assert result["mount_path"] == "/data"
    assert result["read_only"] is False


# Test 12: Container health monitoring
def test_monitor_container_health(orchestrator, sample_container_config):
    """Test container health monitoring"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    health_status = orchestrator.monitor_container_health(container_id)

    assert health_status["container_id"] == container_id
    assert health_status["healthy"] is True
    assert health_status["state"] == ContainerState.RUNNING.value
    assert "metrics" in health_status


# Test 13: Auto-healing healthy container
def test_auto_heal_healthy_container(orchestrator, sample_container_config):
    """Test auto-healing for healthy container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    health_status = {
        "container_id": container_id,
        "healthy": True,
        "metrics": {
            "cpu_usage_percent": 50,
            "memory_usage_mb": 500,
            "memory_limit_mb": 2048
        }
    }

    result = orchestrator.auto_heal_container(container_id, health_status)

    assert result["success"] is True
    assert result["action"] == "none"
    assert result["reason"] == "Container is healthy"


# Test 14: Auto-healing unhealthy container
def test_auto_heal_unhealthy_container(orchestrator, sample_container_config):
    """Test auto-healing for unhealthy container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    health_status = {
        "container_id": container_id,
        "healthy": False,
        "metrics": {}
    }

    result = orchestrator.auto_heal_container(container_id, health_status)

    assert result["success"] is True
    assert result["action"] == "restart"
    assert "Container was unhealthy" in result["reason"]


# Test 15: Resource allocation
def test_allocate_resources(orchestrator, sample_container_config):
    """Test resource allocation to container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)

    result = orchestrator.allocate_resources(container_id, "1.0", "512Mi", gpu_limit=1)

    assert result["success"] is True
    assert result["cpu_limit"] == "1.0"
    assert result["memory_limit"] == "512Mi"
    assert result["gpu_limit"] == 1


# Test 16: Build container image
def test_build_container_image(orchestrator):
    """Test building container image"""
    image_id = orchestrator.build_container_image(
        "/path/to/Dockerfile",
        "test-image:v1.0",
        {"BUILD_ENV": "production"}
    )

    assert image_id is not None
    assert image_id in orchestrator.images
    assert orchestrator.images[image_id]["tag"] == "test-image:v1.0"


# Test 17: Push image to registry
def test_push_image_to_registry(orchestrator):
    """Test pushing image to registry"""
    result = orchestrator.push_image_to_registry(
        "test-image:v1.0",
        "docker.io",
        {"username": "user", "password": "pass"}
    )

    assert result["success"] is True
    assert result["image"] == "test-image:v1.0"
    assert result["registry"] == "docker.io"
    assert "digest" in result


# Test 18: Pull image from registry
def test_pull_image_from_registry(orchestrator):
    """Test pulling image from registry"""
    result = orchestrator.pull_image_from_registry("nginx:latest", "docker.io")

    assert result["success"] is True
    assert result["image"] == "docker.io/nginx:latest"
    assert "image_id" in result


# Test 19: Tag container image
def test_tag_container_image(orchestrator):
    """Test tagging container image"""
    # First build an image
    image_id = orchestrator.build_container_image(
        "/path/to/Dockerfile",
        "test-image:v1.0",
        {}
    )

    # Then tag it
    result = orchestrator.tag_container_image("test-image:v1.0", "test-image:latest")

    assert result["success"] is True
    assert result["target_tag"] == "test-image:latest"


# Test 20: Docker Compose orchestration
def test_orchestrate_docker_compose(orchestrator):
    """Test Docker Compose orchestration"""
    result = orchestrator.orchestrate_docker_compose(
        "/path/to/docker-compose.yml",
        "test-project"
    )

    assert result["success"] is True
    assert result["project_name"] == "test-project"
    assert len(result["services"]) > 0


# Test 21: Deploy Kubernetes service
def test_deploy_kubernetes_service(orchestrator):
    """Test deploying Kubernetes service"""
    service_spec = {
        "metadata": {"name": "test-service"},
        "spec": {
            "type": "ClusterIP",
            "selector": {"app": "test"},
            "ports": [{"port": 80, "targetPort": 80}]
        }
    }

    result = orchestrator.deploy_kubernetes_service(service_spec, "default")

    assert result["success"] is True
    assert result["service_name"] == "test-service"
    assert result["type"] == "ClusterIP"


# Test 22: Configure service discovery
def test_configure_service_discovery(orchestrator):
    """Test service discovery configuration"""
    discovery_config = {
        "type": "dns",
        "health_check": {"path": "/health", "interval": 10},
        "tags": ["web", "production"]
    }

    result = orchestrator.configure_service_discovery("test-service", discovery_config)

    assert result["success"] is True
    assert result["discovery_type"] == "dns"


# Test 23: Setup load balancing
def test_setup_load_balancing(orchestrator):
    """Test load balancing setup"""
    lb_config = {
        "type": "round-robin",
        "algorithm": "least-connections",
        "health_check": {"interval": 30},
        "session_affinity": True
    }

    result = orchestrator.setup_load_balancing("test-service", lb_config)

    assert result["success"] is True
    assert result["lb_type"] == "round-robin"
    assert "external_ip" in result


# Test 24: Enable Horizontal Pod Autoscaling
def test_enable_horizontal_pod_autoscaling(orchestrator, sample_deployment_spec):
    """Test enabling HPA"""
    orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    result = orchestrator.enable_horizontal_pod_autoscaling(
        "test-deployment",
        min_replicas=2,
        max_replicas=10,
        target_cpu=80,
        namespace="default"
    )

    assert result["success"] is True
    assert result["min_replicas"] == 2
    assert result["max_replicas"] == 10
    assert result["target_cpu"] == 80


# Test 25: Enable Vertical Pod Autoscaling
def test_enable_vertical_pod_autoscaling(orchestrator, sample_deployment_spec):
    """Test enabling VPA"""
    orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    vpa_config = {
        "update_mode": "Auto",
        "resource_policy": {
            "containerPolicies": [
                {
                    "containerName": "nginx",
                    "minAllowed": {"cpu": "100m", "memory": "50Mi"}
                }
            ]
        }
    }

    result = orchestrator.enable_vertical_pod_autoscaling(
        "test-deployment",
        vpa_config,
        namespace="default"
    )

    assert result["success"] is True
    assert result["update_mode"] == "Auto"


# Test 26: Execute rolling update
def test_execute_rolling_update(orchestrator, sample_deployment_spec):
    """Test executing rolling update"""
    orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    result = orchestrator.execute_rolling_update(
        "test-deployment",
        "nginx:1.19",
        namespace="default"
    )

    assert result["success"] is True
    assert result["new_image"] == "nginx:1.19"
    assert result["state"] == "Available"


# Test 27: Rollback deployment
def test_rollback_deployment(orchestrator, sample_deployment_spec):
    """Test deployment rollback"""
    orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    result = orchestrator.rollback_deployment(
        "test-deployment",
        revision=1,
        namespace="default"
    )

    assert result["success"] is True
    assert result["revision"] == 1
    assert result["state"] == "Available"


# Test 28: Create ConfigMap
def test_create_configmap(orchestrator):
    """Test creating Kubernetes ConfigMap"""
    data = {
        "config.yml": "key: value",
        "app.properties": "app.name=test"
    }

    result = orchestrator.create_configmap("test-config", data, "default")

    assert result["success"] is True
    assert result["configmap_name"] == "test-config"
    assert len(result["data_keys"]) == 2


# Test 29: Create Secret
def test_create_secret(orchestrator):
    """Test creating Kubernetes Secret"""
    data = {
        "username": "admin",
        "password": "secret123"
    }

    result = orchestrator.create_secret("test-secret", data, "Opaque", "default")

    assert result["success"] is True
    assert result["secret_name"] == "test-secret"
    assert result["type"] == "Opaque"
    assert len(result["data_keys"]) == 2


# Test 30: Create Persistent Volume Claim
def test_create_persistent_volume_claim(orchestrator):
    """Test creating PVC"""
    pvc_spec = {
        "metadata": {"name": "test-pvc"},
        "spec": {
            "storageClassName": "standard",
            "accessModes": ["ReadWriteOnce"],
            "resources": {"requests": {"storage": "10Gi"}}
        }
    }

    result = orchestrator.create_persistent_volume_claim(pvc_spec, "default")

    assert result["success"] is True
    assert result["pvc_name"] == "test-pvc"
    assert result["storage_size"] == "10Gi"
    assert result["status"] == "Bound"


# Test 31: Deploy StatefulSet
def test_deploy_statefulset(orchestrator):
    """Test deploying StatefulSet"""
    statefulset_spec = {
        "metadata": {"name": "test-statefulset"},
        "spec": {
            "serviceName": "test-service",
            "replicas": 3,
            "selector": {"matchLabels": {"app": "test"}},
            "template": {
                "metadata": {"labels": {"app": "test"}},
                "spec": {"containers": [{"name": "nginx", "image": "nginx:latest"}]}
            }
        }
    }

    result = orchestrator.deploy_statefulset(statefulset_spec, "default")

    assert result["success"] is True
    assert result["statefulset_name"] == "test-statefulset"
    assert result["replicas"] == 3


# Test 32: Deploy DaemonSet
def test_deploy_daemonset(orchestrator):
    """Test deploying DaemonSet"""
    daemonset_spec = {
        "metadata": {"name": "test-daemonset"},
        "spec": {
            "selector": {"matchLabels": {"app": "test"}},
            "template": {
                "metadata": {"labels": {"app": "test"}},
                "spec": {"containers": [{"name": "nginx", "image": "nginx:latest"}]}
            }
        }
    }

    result = orchestrator.deploy_daemonset(daemonset_spec, "default")

    assert result["success"] is True
    assert result["daemonset_name"] == "test-daemonset"
    assert result["ready"] > 0


# Test 33: Create Job
def test_create_job(orchestrator):
    """Test creating Kubernetes Job"""
    job_spec = {
        "metadata": {"name": "test-job"},
        "spec": {
            "completions": 1,
            "parallelism": 1,
            "template": {
                "spec": {
                    "containers": [{"name": "busybox", "image": "busybox", "command": ["echo", "hello"]}],
                    "restartPolicy": "Never"
                }
            }
        }
    }

    result = orchestrator.create_job(job_spec, "default")

    assert result["success"] is True
    assert result["job_name"] == "test-job"
    assert result["status"] == "Complete"


# Test 34: Create CronJob
def test_create_cronjob(orchestrator):
    """Test creating Kubernetes CronJob"""
    cronjob_spec = {
        "metadata": {"name": "test-cronjob"},
        "spec": {
            "schedule": "0 */6 * * *",
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{"name": "busybox", "image": "busybox", "command": ["echo", "hello"]}],
                            "restartPolicy": "Never"
                        }
                    }
                }
            }
        }
    }

    result = orchestrator.create_cronjob(cronjob_spec, "default")

    assert result["success"] is True
    assert result["cronjob_name"] == "test-cronjob"
    assert result["schedule"] == "0 */6 * * *"


# Test 35: Apply Network Policy
def test_apply_network_policy(orchestrator):
    """Test applying Kubernetes Network Policy"""
    policy_spec = {
        "metadata": {"name": "test-policy"},
        "spec": {
            "podSelector": {"matchLabels": {"app": "test"}},
            "policyTypes": ["Ingress", "Egress"],
            "ingress": [{"from": [{"podSelector": {"matchLabels": {"role": "frontend"}}}]}]
        }
    }

    result = orchestrator.apply_network_policy(policy_spec, "default")

    assert result["success"] is True
    assert result["policy_name"] == "test-policy"


# Test 36: Integrate Istio service mesh
def test_integrate_istio_service_mesh(orchestrator):
    """Test Istio service mesh integration"""
    service_config = {
        "sidecar_injection": True,
        "mtls_mode": "STRICT",
        "telemetry_enabled": True
    }

    result = orchestrator.integrate_service_mesh("istio", service_config)

    assert result["success"] is True
    assert result["mesh_type"] == "istio"
    assert result["enabled"] is True


# Test 37: Integrate Linkerd service mesh
def test_integrate_linkerd_service_mesh(orchestrator):
    """Test Linkerd service mesh integration"""
    service_config = {
        "proxy_injection": True,
        "tap_enabled": True
    }

    result = orchestrator.integrate_service_mesh("linkerd", service_config)

    assert result["success"] is True
    assert result["mesh_type"] == "linkerd"


# Test 38: Integrate Consul service mesh
def test_integrate_consul_service_mesh(orchestrator):
    """Test Consul service mesh integration"""
    service_config = {
        "connect_enabled": True,
        "acl_enabled": True
    }

    result = orchestrator.integrate_service_mesh("consul", service_config)

    assert result["success"] is True
    assert result["mesh_type"] == "consul"


# Test 39: Registry login
def test_manage_container_registry_login(orchestrator):
    """Test container registry login"""
    credentials = {
        "username": "testuser",
        "password": "testpass"
    }

    result = orchestrator.manage_container_registry(
        "docker.io",
        "login",
        credentials
    )

    assert result["success"] is True
    assert result["operation"] == "login"
    assert result["authenticated"] is True


# Test 40: Registry logout
def test_manage_container_registry_logout(orchestrator):
    """Test container registry logout"""
    result = orchestrator.manage_container_registry("docker.io", "logout")

    assert result["success"] is True
    assert result["operation"] == "logout"
    assert result["authenticated"] is False


# Test 41: Scale deployment
def test_scale_deployment(orchestrator, sample_deployment_spec):
    """Test scaling Kubernetes deployment"""
    orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    result = orchestrator.scale_deployment("test-deployment", 5, "default")

    assert result["success"] is True
    assert result["old_replicas"] == 3
    assert result["new_replicas"] == 5


# Test 42: Get container logs
def test_get_container_logs(orchestrator, sample_container_config):
    """Test retrieving container logs"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    logs = orchestrator.get_container_logs(container_id, tail=100)

    assert logs is not None
    assert len(logs) > 0
    assert container_id in logs


# Test 43: Execute command in container
def test_execute_command_in_container(orchestrator, sample_container_config):
    """Test executing command in container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    result = orchestrator.execute_command_in_container(
        container_id,
        ["echo", "hello"]
    )

    assert result["success"] is True
    assert result["exit_code"] == 0


# Test 44: Inspect container
def test_inspect_container(orchestrator, sample_container_config):
    """Test inspecting container"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)

    result = orchestrator.inspect_container(container_id)

    assert result["success"] is True
    assert "container" in result
    assert "metrics" in result


# Test 45: Generate orchestration report
def test_generate_orchestration_report(orchestrator, sample_container_config, sample_deployment_spec):
    """Test generating orchestration report"""
    orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.create_kubernetes_deployment(sample_deployment_spec, "default")

    cluster_info = {
        "nodes": 3,
        "version": "1.24.0"
    }

    report = orchestrator.generate_orchestration_report(cluster_info)

    assert report is not None
    assert "CONTAINER ORCHESTRATION REPORT" in report
    assert "DOCKER CONTAINERS" in report
    assert "KUBERNETES RESOURCES" in report


# Test 46: Validate FSA
def test_validate_fsa(orchestrator):
    """Test FSA validation"""
    result = orchestrator.validate()

    assert result is True


# Test 47: Error handling
def test_error_handling(orchestrator):
    """Test error handling"""
    exception = ValueError("Test error")
    result = orchestrator.error_handling(exception)

    assert result["success"] is False
    assert result["error"] == "Test error"
    assert result["error_type"] == "ValueError"


# Test 48: Execute with Docker platform
def test_execute_docker_operation(orchestrator, sample_container_config):
    """Test execute method with Docker platform"""
    orchestration_config = {
        "operation": "create",
        "platform": "docker",
        "config": {
            "image": "nginx:latest",
            "container_config": sample_container_config
        }
    }

    result = orchestrator.execute(orchestration_config)

    assert result["success"] is True
    assert result["platform"] == "docker"


# Test 49: Execute with Kubernetes platform
def test_execute_kubernetes_operation(orchestrator, sample_deployment_spec):
    """Test execute method with Kubernetes platform"""
    orchestration_config = {
        "operation": "create",
        "platform": "kubernetes",
        "config": {
            "resource_type": "deployment",
            "spec": sample_deployment_spec,
            "namespace": "default"
        }
    }

    result = orchestrator.execute(orchestration_config)

    assert result["success"] is True
    assert result["platform"] == "kubernetes"


# Test 50: Execute with Docker Compose
def test_execute_compose_operation(orchestrator):
    """Test execute method with Docker Compose"""
    orchestration_config = {
        "operation": "deploy",
        "platform": "compose",
        "config": {
            "compose_file": "/path/to/docker-compose.yml",
            "project_name": "test-project"
        }
    }

    result = orchestrator.execute(orchestration_config)

    assert result["success"] is True


# Test 51: Container not found error
def test_container_not_found_error(orchestrator):
    """Test error when container not found"""
    with pytest.raises(ValueError, match="Container not found"):
        orchestrator.start_container("nonexistent-container-id")


# Test 52: Deployment not found error
def test_deployment_not_found_error(orchestrator):
    """Test error when deployment not found"""
    with pytest.raises(ValueError, match="Deployment not found"):
        orchestrator.scale_deployment("nonexistent-deployment", 5, "default")


# Test 53: Parse CPU limit
def test_parse_cpu_limit(orchestrator):
    """Test CPU limit parsing"""
    # Test millicores
    result = orchestrator._parse_cpu_limit("500m")
    assert result == 0.5

    # Test cores
    result = orchestrator._parse_cpu_limit("2.0")
    assert result == 2.0


# Test 54: Parse memory limit
def test_parse_memory_limit(orchestrator):
    """Test memory limit parsing"""
    # Test MiB
    result = orchestrator._parse_memory_limit("512Mi")
    assert result == 512 * 1024 * 1024

    # Test GiB
    result = orchestrator._parse_memory_limit("2Gi")
    assert result == 2 * 1024 * 1024 * 1024


# Test 55: Multi-container orchestration
def test_multi_container_orchestration(orchestrator):
    """Test orchestrating multiple containers"""
    containers = []

    for i in range(3):
        config = {
            "name": f"container-{i}",
            "command": ["python", "app.py"],
            "environment": {"INDEX": str(i)}
        }
        container_id = orchestrator.create_container(f"nginx:latest", config)
        orchestrator.start_container(container_id)
        containers.append(container_id)

    assert len(containers) == 3
    for container_id in containers:
        assert orchestrator.containers[container_id]["state"] == ContainerState.RUNNING.value


# Test 56: High availability deployment
def test_high_availability_deployment(orchestrator):
    """Test high-availability deployment with multiple replicas"""
    deployment_spec = {
        "metadata": {"name": "ha-deployment"},
        "spec": {
            "replicas": 5,
            "selector": {"matchLabels": {"app": "ha"}},
            "template": {
                "metadata": {"labels": {"app": "ha"}},
                "spec": {"containers": [{"name": "nginx", "image": "nginx:latest"}]}
            }
        }
    }

    result = orchestrator.create_kubernetes_deployment(deployment_spec, "default")

    assert result["success"] is True
    assert result["replicas"] == 5


# Test 57: Resource-constrained deployment
def test_resource_constrained_deployment(orchestrator, sample_container_config):
    """Test deployment with resource constraints"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)

    # Allocate minimal resources
    result = orchestrator.allocate_resources(container_id, "100m", "64Mi")

    assert result["success"] is True
    assert result["cpu_limit"] == "100m"
    assert result["memory_limit"] == "64Mi"


# Test 58: GPU container orchestration
def test_gpu_container_orchestration(orchestrator, sample_container_config):
    """Test orchestrating container with GPU resources"""
    container_id = orchestrator.create_container("tensorflow:latest-gpu", sample_container_config)

    result = orchestrator.allocate_resources(container_id, "4.0", "16Gi", gpu_limit=2)

    assert result["success"] is True
    assert result["gpu_limit"] == 2


# Test 59: Container metrics collection
def test_container_metrics_collection(orchestrator, sample_container_config):
    """Test collecting container metrics"""
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    orchestrator.start_container(container_id)

    # Monitor health to collect metrics
    health_status = orchestrator.monitor_container_health(container_id)

    assert "metrics" in health_status
    assert "cpu_usage_percent" in health_status["metrics"]
    assert "memory_usage_mb" in health_status["metrics"]


# Test 60: End-to-end container lifecycle
def test_end_to_end_container_lifecycle(orchestrator, sample_container_config):
    """Test complete container lifecycle from creation to removal"""
    # Create
    container_id = orchestrator.create_container("nginx:latest", sample_container_config)
    assert container_id in orchestrator.containers

    # Start
    start_result = orchestrator.start_container(container_id)
    assert start_result["success"] is True

    # Monitor health
    health_status = orchestrator.monitor_container_health(container_id)
    assert health_status["healthy"] is True

    # Restart
    restart_result = orchestrator.restart_container(container_id)
    assert restart_result["success"] is True

    # Stop
    stop_result = orchestrator.stop_container(container_id)
    assert stop_result["success"] is True

    # Remove
    remove_result = orchestrator.remove_container(container_id, force=True)
    assert remove_result["success"] is True
    assert container_id not in orchestrator.containers
