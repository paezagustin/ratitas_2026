
import git


def commit_to_git(name_commit = 'Update notebooks'):
    repo = git.Repo('/home/lci1/JA/ratitas_2026')
    repo.git.add()
    repo.index.commit(name_commit)
    repo.git.push()

if __name__ == "__main__":
    commit_to_git()
    