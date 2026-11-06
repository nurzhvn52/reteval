# Jenkins server for reteval

Jenkins runs in a container and builds images through the host Docker daemon
(`/var/run/docker.sock`). It is configured as code: [`jenkins.yaml`](jenkins.yaml) creates the
admin user and a multibranch pipeline that scans the repository every 2 minutes and builds
every branch with a `Jenkinsfile`.

```bash
cd ci/jenkins
JENKINS_PORT=8081 docker compose up -d --build     # default port is 8080
```

Open http://localhost:8081 and log in as `admin` (password `admin`, change it with
`JENKINS_ADMIN_PASSWORD`). The first build starts after the first scan.

**Local use only.** The container runs as root with the Docker socket mounted, which gives
it full control of the host's Docker. The port is bound to 127.0.0.1.

## Kubernetes stage (optional)

The stage runs when `kubectl` in the Jenkins container can reach a cluster. With
[kind](https://kind.sigs.k8s.io/):

```bash
kind create cluster --name reteval
docker network connect kind reteval-jenkins
kind get kubeconfig --internal --name reteval \
  | docker exec -i reteval-jenkins sh -c 'mkdir -p /var/jenkins_home/.kube && cat > /var/jenkins_home/.kube/config'
```

Keep the client within one minor version of the cluster: `KUBECTL_VERSION` build argument.

## Docker Hub (optional)

Add a "Username with password" credential with ID `dockerhub` (Docker Hub user name and an
access token) under Manage Jenkins, Credentials, then run the job with `PUSH_IMAGE` ticked.
The image is pushed as `<user>/reteval:<short sha>` and `:latest`.
