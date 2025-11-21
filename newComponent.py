import os

def main():
    # Get package name and category from user
    package_name = input("Enter the package name: ")
    category = input("Enter the category: ")

    # Create the directory path if it doesn't exist
    directory_path = f"src/{category}/{package_name}"
    os.makedirs(directory_path, exist_ok=True)

    # Create the directory threads path if it doesn't exist
    directory_path_threads = f"src/{category}/{package_name}/threads"
    os.makedirs(directory_path_threads, exist_ok=True)

    # Create and open the new Python file for the package
    file_path = os.path.join(directory_path, f"process{package_name}.py")
    with open(file_path, 'w') as file:
        file.write(f'if __name__ == "__main__":\n')
        file.write(f'    import sys\n')
        file.write(f'    sys.path.insert(0, "../../..")\n\n')
        file.write(f'from src.templates.workerprocess import WorkerProcess\n')
        file.write(f'from src.{category}.{package_name}.threads.thread{package_name} import thread{package_name}\n\n')
        file.write(f'class process{package_name}(WorkerProcess):\n')
        file.write(f'    """This process handles {package_name}.\n')
        file.write(f'    Args:\n')
        file.write(f'        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.\n')
        file.write(f'        logging (logging object): Made for debugging.\n')
        file.write(f'        debugging (bool, optional): A flag for debugging. Defaults to False.\n')
        file.write(f'    """\n\n')
        file.write(f'    def __init__(self, queueList, logging, ready_event=None, debugging=False):\n')
        file.write(f'        self.queuesList = queueList\n')
        file.write(f'        self.logging = logging\n')
        file.write(f'        self.debugging = debugging\n')
        file.write(f'        super(process{package_name}, self).__init__(self.queuesList, ready_event)\n\n')
        file.write(f'    def state_change_handler(self):\n')
        file.write(f'        pass\n\n')
        file.write(f'    def process_work(self):\n')
        file.write(f'        pass\n\n')
        file.write(f'    def _init_threads(self):\n')
        file.write(f'        """Create the {package_name} Publisher thread and add to the list of threads."""\n')
        file.write(f'        {package_name}Th = thread{package_name}(\n')
        file.write(f'            self.queuesList, self.logging, self.debugging\n')
        file.write(f'        )\n')
        file.write(f'        self.threads.append({package_name}Th)\n')

    # Create and open the new Python file for the package
    file_path_threads = os.path.join(directory_path_threads, f"thread{package_name}.py")
    with open(file_path_threads, 'w') as file:
        file.write(f'from src.templates.threadwithstop import ThreadWithStop\n')
        file.write(f'from src.utils.messages.allMessages import (mainCamera)\n')
        file.write(f'from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber\n')
        file.write(f'from src.utils.messages.messageHandlerSender import messageHandlerSender\n\n')
        file.write(f'class thread{package_name}(ThreadWithStop):\n')
        file.write(f'    """This thread handles {package_name}.\n')
        file.write(f'    Args:\n')
        file.write(f'        queueList (dictionary of multiprocessing.queues.Queue): Dictionary of queues where the ID is the type of messages.\n')
        file.write(f'        logging (logging object): Made for debugging.\n')
        file.write(f'        debugging (bool, optional): A flag for debugging. Defaults to False.\n')
        file.write(f'    """\n\n')
        file.write(f'    def __init__(self, queueList, logging, debugging=False):\n')
        file.write(f'        self.queuesList = queueList\n')
        file.write(f'        self.logging = logging\n')
        file.write(f'        self.debugging = debugging\n')
        file.write(f'        self.subscribe()\n')
        file.write(f'        super(thread{package_name}, self).__init__()\n\n')
        file.write(f'    def subscribe(self):\n')
        file.write(f'        """Subscribes to the messages you are interested in"""\n')
        file.write(f'        pass\n\n')
        file.write(f'    def state_change_handler(self):\n')
        file.write(f'        pass\n\n')
        file.write(f'    def thread_work(self):\n')
        file.write(f'        pass\n\n')

    # Read the main.py file
    main_py_path = "main.py"
    if not os.path.exists(main_py_path):
        print("The main.py file does not exist.")
        return

    with open(main_py_path, 'r') as file:
        lines = file.readlines()

    # Add import to the lines
    import_line = f"from src.{category}.{package_name}.process{package_name} import process{package_name}\n"
    run_line = f"{package_name}_ready = Event()\nprocess{package_name} = process{package_name}(queueList, logging, {package_name}_ready, debugging = False)\nallProcesses.insert(0, process{package_name})\n"

    import_index = run_index = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "# ------ New component imports ends here ------#" or stripped == "# ------ New component imports ends here ------ #":
            import_index = i
        if stripped == "# ------ New component initialize ends here ------#" or stripped == "# ------ New component initialize ends here ------ #":
            run_index = i

    # Insert in reverse order
    if run_index is not None:
        lines.insert(run_index, run_line)
        lines.insert(run_index+1, "\n")
    if import_index is not None:
        if lines[import_index-1].strip() == "":
            lines.insert(import_index-1, import_line)
        else:
            lines.insert(import_index, import_line)
            lines.insert(import_index+1, "\n")

    # Write back to main.py
    with open(main_py_path, 'w') as file:
        file.writelines(lines)

    print("File created and main.py updated.")

if __name__ == "__main__":
    main()
