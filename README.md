# kubelet-auth-daemonset

An example Helm chart that creates a DaemonSet that will place Docker registry credentials on each
node in order to avoid requiring the use of imagePullSecrets or other mechanisms for pulling images
from private registries. This is most useful in corporate/enterprise environments where all images
come from a private registry, but that registry isn't particularly "secret".

This example uses an ExternalSecret from `kubernetes-external-secret`, but any Kubernetes Secret
that contains the following keys will work:

* `username`: The username for Basic Auth
* `password`: The password for Basic Auth
* `registries`: A comma separated list of Docker registries to use the above credentials for.
