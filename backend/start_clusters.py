import os
import subprocess
import time
import json
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def start_process(cmd, cwd=None, env=None):
    try:
        env = env or os.environ.copy()
        env["PYTHONPATH"] = BASE_DIR
        return subprocess.Popen(cmd, cwd=cwd or BASE_DIR, env=env)
    except Exception as e:
        print(f"[ERROR] Failed to start process: {' '.join(cmd)} — {e}")
        return None

def get_free_ports(start, count):
    try:
        return [start + i for i in range(count)]
    except Exception as e:
        print(f"[ERROR] Failed to compute free ports: {e}")
        return []

def launch_nodes(cluster_id, node_ports):
    processes = []
    for port in node_ports:
        try:
            print(f"Starting storage node on port {port}...")
            p = start_process(["python", "dfs/nodes/node_storage.py", "--port", str(port)])
            if p:
                processes.append(p)
            else:
                print(f"[WARNING] Could not start node on port {port}")
        except Exception as e:
            print(f"[ERROR] Failed to launch node on port {port}: {e}")
    return processes

def launch_cluster_manager(cluster_port, node_ports):
    try:
        node_urls = json.dumps([f"http://localhost:{port}" for port in node_ports])
        env = os.environ.copy()
        env["NODES"] = node_urls
        env["PYTHONPATH"] = BASE_DIR
        print(f"Starting cluster manager on port {cluster_port}...")
        return start_process(["python", "dfs/load_balancers/cluster_manager.py", "--port", str(cluster_port)], env=env)
    except Exception as e:
        print(f"[ERROR] Failed to launch cluster manager on port {cluster_port}: {e}")
        return None

def launch_global_balancer(cluster_map):
    try:
        env = os.environ.copy()
        env["CLUSTERS"] = json.dumps(cluster_map)
        env["PYTHONPATH"] = BASE_DIR
        print("Starting global load balancer on port 6000...")
        return start_process(["python", "dfs/load_balancers/global_balancer.py", "--port", "6000"], env=env)
    except Exception as e:
        print(f"[ERROR] Failed to launch global load balancer: {e}")
        return None

def start_clusters_and_nodes():
    print("Starting clusters and nodes...")
    try:
        clusters = int(input("How many clusters do you want to start? ").strip())
        nodes_per_cluster = int(input("How many nodes per cluster? ").strip())
    except ValueError:
        print("[ERROR] Please enter valid numbers.")
        return
    except Exception as e:
        print(f"[ERROR] Unexpected error while reading input: {e}")
        return

    node_base_port = 5001
    cluster_base_port = 7001

    all_node_processes = []
    cluster_managers = []
    cluster_map = {}

    for c in range(clusters):
        try:
            node_ports = get_free_ports(node_base_port + c * nodes_per_cluster, nodes_per_cluster)
            cluster_port = cluster_base_port + c

            # Launch cluster manager
            cm_process = launch_cluster_manager(cluster_port, node_ports)
            if cm_process:
                cluster_managers.append(cm_process)
            else:
                print(f"[WARNING] Cluster manager for cluster {c+1} not started.")

            # Launch nodes for this cluster
            node_processes = launch_nodes(c, node_ports)
            all_node_processes.extend(node_processes)

            # Register cluster
            cluster_map[f"cluster_{c+1}"] = f"http://localhost:{cluster_port}"

            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Failed to set up cluster {c+1}: {e}")

    try:
        global_balancer = launch_global_balancer(cluster_map)
        time.sleep(1)
    except Exception as e:
        global_balancer = None
        print(f"[ERROR] Could not launch global balancer: {e}")

    print("\n✅ System is live!")

    # Keep running the system
    try:
        while True:
            time.sleep(60)  # Check every 60 seconds
            print("Clusters and nodes are running...")
    except KeyboardInterrupt:
        print("\nShutting down clusters and nodes...")
    except Exception as e:
        print(f"[ERROR] Runtime failure: {e}")
    finally:
        for p in all_node_processes + cluster_managers + ([global_balancer] if global_balancer else []):
            try:
                if p:
                    p.terminate()
            except Exception as e:
                print(f"[ERROR] Failed to terminate process: {e}")

if __name__ == "__main__":
    try:
        start_clusters_and_nodes()
    except Exception as e:
        print(f"[FATAL] Failed to start the system: {e}")
