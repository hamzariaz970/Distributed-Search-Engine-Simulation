import os
import subprocess
import time
import sys
import json
from dfs.core.chunker import reconstruct_file

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
        p = start_process(["python", "nodes/node_storage.py", "--port", str(port)])
        if p: processes.append(p)
    return processes

def launch_cluster_manager(cluster_port, node_ports):
    node_urls = json.dumps([f"http://localhost:{port}" for port in node_ports])
    env = os.environ.copy()
    env["NODES"] = node_urls
    env["PYTHONPATH"] = BASE_DIR
    print(f"Starting cluster manager on port {cluster_port}...")
    return start_process(["python", "load_balancers/cluster_manager.py", "--port", str(cluster_port)], env=env)

def launch_global_balancer(cluster_map):
    env = os.environ.copy()
    env["CLUSTERS"] = json.dumps(cluster_map)
    env["PYTHONPATH"] = BASE_DIR
    print("Starting global load balancer on port 6000...")
    return start_process(["python", "load_balancers/global_balancer.py", "--port", "6000"], env=env)

def upload_file():
    file_path = input("Enter filename (from tests/input_files/): ").strip()
    full_path = os.path.join(BASE_DIR, "tests", "input_files", file_path)
    if not os.path.exists(full_path):
        print(f"[ERROR] File not found: {full_path}")
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = BASE_DIR
    subprocess.run(["python", "client/upload.py", file_path], env=env)

def list_uploaded_files():
    metadata_dir = os.path.join(BASE_DIR, "metadata")
    if not os.path.exists(metadata_dir):
        print("No metadata directory found.")
        return

    files = [f for f in os.listdir(metadata_dir) if f.endswith(".json")]
    if not files:
        print("No uploaded files found.")
        return

    print("\nUploaded Files:")
    for i, f in enumerate(files):
        print(f"[{i+1}] {f.replace('.json', '')}")
    choice = input("Enter file number to view metadata (or press Enter to cancel): ").strip()
    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(files):
            path = os.path.join(metadata_dir, files[index])
            with open(path) as f:
                data = json.load(f)
                print(json.dumps(data, indent=2))

def download_file():
    import re
    metadata_dir = os.path.join(BASE_DIR, "metadata")
    output_dir = os.path.join(BASE_DIR, "tests", "output_files")
    chunk_dir = os.path.join(BASE_DIR, "chunks")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(chunk_dir, exist_ok=True)

    files = [f for f in os.listdir(metadata_dir) if f.endswith(".json")]
    if not files:
        print("[INFO] No uploaded files found.")
        return

    print("\nAvailable uploaded files:")
    for i, f in enumerate(files):
        print(f"[{i+1}] {f.replace('.json', '')}")

    choice = input("Enter file number to download: ").strip()
    if not choice.isdigit():
        print("[ERROR] Invalid input.")
        return

    index = int(choice) - 1
    if index < 0 or index >= len(files):
        print("[ERROR] Invalid file number.")
        return

    file_basename = files[index].replace(".json", "")
    metadata_path = os.path.join(metadata_dir, f"{file_basename}.json")

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        def extract_chunk_index(chunk_id):
            match = re.search(r'_chunk(\d+)$', chunk_id)
            return int(match.group(1)) if match else -1

        chunks = sorted(metadata.keys(), key=extract_chunk_index)

        import requests
        for chunk_id in chunks:
            node_url = metadata[chunk_id]
            chunk_path = os.path.join(chunk_dir, chunk_id)

            r = requests.get(f"{node_url}/chunk/{chunk_id}", timeout=5)
            r.raise_for_status()

            with open(chunk_path, "wb") as f:
                f.write(r.content)
            print(f"[OK] Downloaded {chunk_id} from {node_url}")

        from core.chunker import reconstruct_file
        name, ext = os.path.splitext(file_basename)
        output_path = os.path.join(output_dir, f"{name}_reconstructed{ext}")

        if os.path.exists(output_path):
            os.remove(output_path)

        reconstruct_file(chunks, output_path)
        print(f"\n[SUCCESS] File downloaded and reconstructed at: {output_path}")

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")


def delete_distributed_file():
    metadata_dir = os.path.join(BASE_DIR, "metadata")
    chunk_dir = os.path.join(BASE_DIR, "chunks")
    output_dir = os.path.join(BASE_DIR, "tests", "output_files")
    files = [f for f in os.listdir(metadata_dir) if f.endswith(".json")]
    
    if not files:
        print("[INFO] No uploaded files found.")
        return

    print("\nUploaded Files:")
    for i, f in enumerate(files):
        print(f"[{i+1}] {f.replace('.json', '')}")

    choice = input("Enter file number to delete: ").strip()

    if not choice.isdigit():
        print("[ERROR] Invalid input.")
        return

    index = int(choice) - 1
    if index < 0 or index >= len(files):
        print("[ERROR] Invalid file number.")
        return

    file_basename = files[index].replace(".json", "")
    metadata_file = os.path.join(metadata_dir, f"{file_basename}.json")

    confirm = input(f"Are you sure you want to delete '{file_basename}'? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Deletion cancelled.")
        return

    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read metadata: {e}")
        return

    failed = []
    for chunk_id, node_url in metadata.items():
        try:
            import requests
            r = requests.delete(f"{node_url}/chunk/{chunk_id}", timeout=5)
            if r.status_code == 200:
                print(f"[OK] Deleted {chunk_id} from {node_url}")
            else:
                failed.append(chunk_id)
                print(f"[WARN] Chunk {chunk_id} deletion failed with status {r.status_code}")
        except Exception as e:
            failed.append(chunk_id)
            print(f"[ERROR] Could not delete {chunk_id}: {e}")

    if failed:
        print(f"[FAIL] Some chunks could not be deleted: {failed}")
    else:
        os.remove(metadata_file)
        print(f"[SUCCESS] Metadata for '{file_basename}' deleted.")

        # Delete local chunks
        for chunk_id in metadata:
            local_path = os.path.join(chunk_dir, chunk_id)
            if os.path.exists(local_path):
                os.remove(local_path)

        # Delete reconstructed output file
        name, ext = os.path.splitext(file_basename)
        reconstructed_file = os.path.join(output_dir, f"{name}_reconstructed{ext}")
        if os.path.exists(reconstructed_file):
            os.remove(reconstructed_file)
            print(f"[CLEANUP] Deleted reconstructed file: {reconstructed_file}")

        print("[CLEANUP] Local chunks deleted.")


def main():
    print("DFS Launcher")
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
    while True:
        print("\nOptions:")
        print("1. Upload file")
        print("2. List uploaded files")
        print("3. Download file")
        print("4. Delete file")
        print("5. Exit")
        choice = input("Select an option: ").strip()

        if choice == "1":
            upload_file()
        elif choice == "2":
            list_uploaded_files()
        elif choice == "3":
            download_file()
        elif choice == "4":
            delete_distributed_file()
        elif choice == "5":
            print("Shutting down all processes...")
            for p in all_node_processes + cluster_managers + [global_balancer]:
                if p: p.terminate()
            break
        else:
            print("[ERROR] Invalid option. Try again.")

if __name__ == "__main__":
    main()
