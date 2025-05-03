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
    return [start + i for i in range(count)]

def launch_nodes(cluster_id, node_ports):
    processes = []
    for port in node_ports:
        print(f"Starting storage node on port {port}...")
        p = start_process(["python", "dfs/nodes/node_storage.py", "--port", str(port)])
        if p: processes.append(p)
    return processes

def launch_cluster_manager(cluster_port, node_ports):
    node_urls = json.dumps([f"http://localhost:{port}" for port in node_ports])
    env = os.environ.copy()
    env["NODES"] = node_urls
    env["PYTHONPATH"] = BASE_DIR
    print(f"Starting cluster manager on port {cluster_port}...")
    return start_process(["python", "dfs/load_balancers/cluster_manager.py", "--port", str(cluster_port)], env=env)

def launch_global_balancer(cluster_map):
    env = os.environ.copy()
    env["CLUSTERS"] = json.dumps(cluster_map)
    env["PYTHONPATH"] = BASE_DIR
    print("Starting global load balancer on port 6000...")
    return start_process(["python", "dfs/load_balancers/global_balancer.py", "--port", "6000"], env=env)

def start_clusters_and_nodes():
    print("Starting clusters and nodes...")
    try:
        clusters = int(input("How many clusters do you want to start? ").strip())
        nodes_per_cluster = int(input("How many nodes per cluster? ").strip())
    except ValueError:
        print("[ERROR] Please enter valid numbers.")
        return

    node_base_port = 5001
    cluster_base_port = 7001

    all_node_processes = []
    cluster_managers = []
    cluster_map = {}

    for c in range(clusters):
        node_ports = get_free_ports(node_base_port + c * nodes_per_cluster, nodes_per_cluster)
        cluster_port = cluster_base_port + c

        # Launch cluster manager
        cm_process = launch_cluster_manager(cluster_port, node_ports)
        cluster_managers.append(cm_process)

        # Launch nodes for this cluster
        node_processes = launch_nodes(c, node_ports)
        all_node_processes.extend(node_processes)

        # Register cluster
        cluster_map[f"cluster_{c+1}"] = f"http://localhost:{cluster_port}"

        time.sleep(1)

    # Launch global balancer with the full map
    global_balancer = launch_global_balancer(cluster_map)
    time.sleep(1)

    print("\n✅ System is live!")

    # Keep running the system
    try:
        while True:
            time.sleep(60)  # Check every 60 seconds, or adjust as needed.
            print("Clusters and nodes are running...")
    except KeyboardInterrupt:
        print("\nShutting down clusters and nodes...")
        for p in all_node_processes + cluster_managers + [global_balancer]:
            if p:
                p.terminate()

if __name__ == "__main__":
    start_clusters_and_nodes()
