from plato.sync_sdk import SyncPlato
from plato.sync_env import SyncPlatoEnvironment

client = SyncPlato()

def main():
    tasks = client.load_tasks("espocrm")
    print(len(tasks))
    env = client.make_environment("espocrm")
    env.wait_for_ready()
    print(env.id)
    env.reset(task=tasks[1])
    env.evaluate()

    # reconstruct a new env
    print("reconstructing env")
    env = SyncPlatoEnvironment.from_id(client, env.id)
    env.evaluate()

if __name__ == "__main__":
    main()