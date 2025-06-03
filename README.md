# Docker Mail Server on Kubernetes with Nginx Ingress and Cert-Manager

## 1. Overview

This guide describes how to deploy a full-featured mail server (`docker-mailserver`) on a Kubernetes cluster. It leverages Nginx Ingress for handling both HTTP/S traffic (for the Rspamd web UI) and TCP passthrough for standard mail protocols (SMTP, IMAP, POP3). Cert-manager is used to automatically provision TLS certificates, specifically for securing the Rspamd Ingress in this setup.

Configuration is managed primarily through a `custom-values.yaml` file for the `docker-mailserver` Helm chart and an `nginx-tcp-services-configmap.yaml` file to configure Nginx for mail protocol routing.

## 2. Prerequisites

*   A running Kubernetes cluster (e.g., v1.20 or newer).
*   `kubectl` command-line tool configured to interact with your cluster.
*   Helm v3 package manager for Kubernetes installed.
*   Nginx Ingress Controller installed in your cluster. Crucially, it must be configured to allow TCP/UDP service passthrough. Refer to the official Nginx Ingress documentation for enabling this, often via a command-line flag like `--tcp-services-configmap=[NGINX_INGRESS_NAMESPACE]/tcp-services`.
*   Cert-manager installed in your cluster (if you intend to use the provided Issuer example for securing Rspamd's Ingress with TLS certificates).
*   A registered domain name (e.g., `xr-kafka.sbs`).
*   A Cloudflare account and API token (this is only required if you are using the provided Cloudflare DNS01 Issuer example for cert-manager; adapt if using a different DNS provider or challenge type).

## 3. DNS Configuration

Proper DNS setup is critical for a functioning mail server. For your domain (e.g., `xr-kafka.sbs`) and mail server hostname (e.g., `webmail.xr-kafka.sbs`), you'll need the following records:

*   **A Record:** Points your mail server's hostname to the external IP address of your Nginx Ingress LoadBalancer.
    *   Example: `webmail.xr-kafka.sbs. IN A [YOUR_INGRESS_LOADBALANCER_IP]`
*   **MX Record:** Directs mail for your domain to your mail server. It should point to the hostname defined in the A record.
    *   Example: `xr-kafka.sbs. IN MX 10 webmail.xr-kafka.sbs.`
*   **PTR Record (Reverse DNS):** Maps the IP address of your Nginx Ingress LoadBalancer back to your mail server's hostname. This is vital for email deliverability and reducing the chances of being marked as spam.
    *   Example: `[LAST_OCTET_OF_IP].[THIRD_OCTET_OF_IP].[SECOND_OCTET_OF_IP].[FIRST_OCTET_OF_IP].in-addr.arpa. IN PTR webmail.xr-kafka.sbs.`
    *   Note: This record is typically configured with your IP address provider (e.g., your cloud provider or ISP).
*   **SPF, DKIM, DMARC Records:**
    *   **SPF (Sender Policy Framework):** Helps prevent email spoofing by specifying which mail servers are authorized to send email for your domain.
    *   **DKIM (DomainKeys Identified Mail):** Adds a digital signature to outgoing emails, allowing receivers to verify that the email originated from an authorized server and hasn't been tampered with.
    *   **DMARC (Domain-based Message Authentication, Reporting & Conformance):** Uses SPF and DKIM to determine the authenticity of an email and provides instructions on how to handle messages that fail these checks.
    *   The setup for SPF, DKIM, and DMARC records is specific to `docker-mailserver`'s internal configuration (e.g., enabling DKIM, retrieving the DKIM public key). Consult the official `docker-mailserver` documentation for detailed instructions on generating and configuring these records.

## 4. Nginx Ingress Controller Setup for TCP Passthrough

The Nginx Ingress controller must be explicitly configured to forward TCP traffic for mail protocols (SMTP, IMAP, POP3, etc.) to your `docker-mailserver` instance.

*   This configuration is achieved using the `nginx-tcp-services-configmap.yaml` file provided in this repository.
*   **Key steps for deploying this ConfigMap:**
    1.  **Modify the ConfigMap:** Open `nginx-tcp-services-configmap.yaml` and replace placeholders like `mail/dms-docker-mailserver` with the correct namespace where your `docker-mailserver` is deployed (e.g., `[DMS_NAMESPACE]`) and the actual service name created by the Helm chart (typically `[YOUR_DMS_RELEASE_NAME]-docker-mailserver`).
    2.  **Apply the ConfigMap:** The ConfigMap itself must be created in the *same namespace where your Nginx Ingress controller pods are running* (e.g., `ingress-nginx`).
        ```bash
        kubectl apply -f nginx-tcp-services-configmap.yaml -n [NGINX_INGRESS_NAMESPACE]
        ```
    3.  **Ensure Nginx Ingress Controller Flag:** Your Nginx Ingress controller deployment (or DaemonSet/StatefulSet) must be started with the `--tcp-services-configmap` argument pointing to this ConfigMap. For example:
        `--tcp-services-configmap=[NGINX_INGRESS_NAMESPACE]/tcp-services`
        (Replace `[NGINX_INGRESS_NAMESPACE]` with the actual namespace, e.g., `ingress-nginx`). If your controller is already running, you may need to update its deployment configuration and restart its pods.

## 5. Cert-Manager Issuer Configuration (for Rspamd Ingress)

This section details how to set up cert-manager to automatically issue and renew a TLS certificate for the Rspamd web UI, which is exposed via an HTTP/S Ingress rule. The example below uses a cert-manager `Issuer` with a Cloudflare DNS01 challenge. You can adapt this for other DNS providers or use an HTTP01 challenge if that's more suitable for your environment.

```yaml
# letsencrypt-prod-issuer.yaml
apiVersion: cert-manager.io/v1
kind: Issuer # Use ClusterIssuer for a cluster-wide issuer if preferred
metadata:
  name: letsencrypt-prod-issuer # Renamed for clarity
  namespace: [CERT_MANAGER_NAMESPACE_OR_DMS_NAMESPACE] # If kind: Issuer, specify the namespace (e.g., cert-manager or where docker-mailserver will run). Not needed for ClusterIssuer.
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: masoud.yari@t-systems.com # USER TO REPLACE: Your valid email address for Let's Encrypt notifications
    privateKeySecretRef:
      name: letsencrypt-prod-private-key # Name of the Kubernetes secret to store the ACME account private key
    solvers:
    - dns01:
        cloudflare:
          email: yourmail@mail.com # USER TO REPLACE: Your Cloudflare account email
          apiTokenSecretRef:
            name: cloudflare-api-token-secret # Name of the Kubernetes secret holding the Cloudflare API token
            key: api-token # Key within the secret that actually holds the token value
```

*   **Steps to use this Issuer:**
    1.  **Create Cloudflare API Token Secret:**
        Replace `[YOUR_CLOUDFLARE_API_TOKEN]` with your actual Cloudflare API token. Ensure the token has permissions to edit DNS records for your domain.
        ```bash
        kubectl create secret generic cloudflare-api-token-secret \
          --namespace [CERT_MANAGER_NAMESPACE_OR_DMS_NAMESPACE] \
          --from-literal=api-token='[YOUR_CLOUDFLARE_API_TOKEN]'
        ```
        (Ensure the namespace matches where you will create the Issuer or is accessible if using ClusterIssuer).
    2.  **Apply the Issuer/ClusterIssuer:**
        Save the YAML above as `letsencrypt-prod-issuer.yaml` (or a similar name).
        ```bash
        kubectl apply -f letsencrypt-prod-issuer.yaml
        ```
    3.  **Reference in `custom-values.yaml`:** Ensure the `rspamd.ingress.annotations` section in your `custom-values.yaml` correctly references this Issuer.
        *   If using a `ClusterIssuer`: `cert-manager.io/cluster-issuer: letsencrypt-prod-issuer`
        *   If using a namespaced `Issuer`: `cert-manager.io/issuer: letsencrypt-prod-issuer` (and ensure Rspamd's Ingress is in the same namespace as the Issuer, or adjust the reference).

## 6. Deploying Docker Mail Server

This setup utilizes the official `docker-mailserver` Helm chart.

*   **Add Helm Repository (if you haven't already):**
    ```bash
    helm repo add docker-mailserver https://docker-mailserver.github.io/docker-mailserver-helm/
    helm repo update
    ```
*   **Deploy the Chart:**
    You will use the `custom-values.yaml` file from this repository to configure your deployment.
    ```bash
    helm install [YOUR_DMS_RELEASE_NAME] docker-mailserver/docker-mailserver \
      --namespace [DMS_NAMESPACE] \
      --create-namespace \
      -f custom-values.yaml
    ```
    *   Replace `[YOUR_DMS_RELEASE_NAME]` with a name for your Helm release (e.g., `dms`).
    *   Replace `[DMS_NAMESPACE]` with the Kubernetes namespace where you want to deploy `docker-mailserver` (e.g., `mail`). The `--create-namespace` flag will create this namespace if it doesn't already exist.
*   **Important:** Before deploying, thoroughly review and **edit `custom-values.yaml`**. Replace all placeholder values (e.g., `mail.yourdomain.com`, `rspamd.yourdomain.com`, Rspamd TLS secret name, timezone, postmaster address, etc.) with your actual information. The file also contains examples for configuring persistence and resource requests/limits, which are highly recommended for production environments.

## 7. Post-Installation Steps

*   **Adding Mail Users:**
    Once `docker-mailserver` is running, you can add email accounts using the following command structure:
    ```bash
    kubectl exec -ti -n [DMS_NAMESPACE] deployment/[YOUR_DMS_RELEASE_NAME]-docker-mailserver -- setup email add user@webmail.xr-kafka.sbs '[PASSWORD]'
    ```
    *   Replace `[DMS_NAMESPACE]` and `[YOUR_DMS_RELEASE_NAME]` with your actual values.
    *   Replace `user@webmail.xr-kafka.sbs` with the desired email address and `[PASSWORD]` with a strong password.
    *   Note: The command targets the deployment. If your pod name is stable and unique (e.g., if not using default replica count), you can target the pod directly: `kubectl exec -ti -n [DMS_NAMESPACE] [YOUR_DMS_POD_NAME] -- setup email add ...`
*   **Testing Mail Flow:**
    *   **Using the Script:** The `mail_test.py` script provided in this repository can be used for a basic SMTP send and IMAP check. Before running, edit the script if your mail server details (`MAIL_SERVER`), email address (`EMAIL_ADDRESS`), or password (`EMAIL_PASSWORD`) differ from the defaults (`webmail.xr-kafka.sbs`, `info@webmail.xr-kafka.sbs`, `test123456`).
        ```bash
        python mail_test.py
        ```
    *   **Mail Client Configuration:** Configure a desktop mail client (like Thunderbird or Outlook) or a webmail client (like Roundcube, if you choose to install one) to connect to your mail server using the host `webmail.xr-kafka.sbs` and the appropriate ports (e.g., 587 for SMTP with STARTTLS, 993 for IMAPS, 465 for SMTPS).
*   **Security Hardening:**
    *   Consult the official `docker-mailserver` documentation for comprehensive security best practices, including topics like Fail2ban configuration, SSL/TLS settings, and anti-spam measures.
    *   Keep `docker-mailserver`, Nginx Ingress, cert-manager, and your Kubernetes cluster components updated to their latest secure versions.
    *   Regularly monitor logs from all components for any suspicious activity. Fail2ban is enabled by default in the provided `custom-values.yaml`, which helps in automatically banning IPs showing malicious behavior.

## 8. Included Configuration Files

This repository contains the following configuration files to aid your deployment:

*   **`README.md`**: This detailed guide.
*   **`custom-values.yaml`**: Custom Helm values for the `docker-mailserver` chart. It includes configurations for environment variables, Rspamd Ingress, and examples for persistence and resource allocation.
*   **`nginx-tcp-services-configmap.yaml`**: An example ConfigMap for setting up Nginx Ingress TCP passthrough for essential mail protocols (SMTP, IMAP, etc.).
*   **`mail_test.py`**: A Python script designed for basic testing of mail sending (SMTP) and receiving/checking (IMAP) functionalities of your deployed mail server.

## 9. Troubleshooting (Basic Tips)

*   **Check Pod Logs:** The first step in troubleshooting is usually to check the logs from the relevant pods:
    *   `docker-mailserver` pods: `kubectl logs -n [DMS_NAMESPACE] -l app.kubernetes.io/name=docker-mailserver` (or target a specific pod name)
    *   Nginx Ingress controller pods: `kubectl logs -n [NGINX_INGRESS_NAMESPACE] -l app.kubernetes.io/name=ingress-nginx`
    *   cert-manager pods (if issues with Rspamd certificate): `kubectl logs -n [CERT_MANAGER_NAMESPACE] -l app.kubernetes.io/name=cert-manager`
*   **Verify DNS Propagation:** Use tools like `dig` (Linux/macOS) or online DNS checkers (e.g., Google Public DNS, MXToolbox) to ensure your DNS records (A, MX, PTR) are correctly configured and have propagated globally.
    ```bash
    dig webmail.xr-kafka.sbs A
    dig xr-kafka.sbs MX
    dig -x [YOUR_INGRESS_LOADBALANCER_IP] # For PTR
    ```
*   **Test Network Connectivity:** Use tools like `telnet` or `nc` (netcat) to check if the mail ports are open and reachable on your Nginx Ingress LoadBalancer IP.
    ```bash
    telnet webmail.xr-kafka.sbs 587
    nc -zv webmail.xr-kafka.sbs 993
    ```
    (Attempt these from an external network to simulate client connections).
*   **Describe Kubernetes Resources:** For detailed status, events, and configuration issues, use `kubectl describe`:
    *   `kubectl describe pod [POD_NAME] -n [DMS_NAMESPACE]`
    *   `kubectl describe service [SERVICE_NAME] -n [DMS_NAMESPACE]`
    *   `kubectl describe ingress [RSPAMD_INGRESS_NAME] -n [DMS_NAMESPACE]`
    *   `kubectl describe issuer letsencrypt-prod-issuer -n [CERT_MANAGER_NAMESPACE_OR_DMS_NAMESPACE]` (if using Issuer)
    *   `kubectl describe certificate [RSPAMD_CERT_NAME] -n [DMS_NAMESPACE]`
*   **Consult `docker-mailserver` Documentation:** The official `docker-mailserver` documentation is an invaluable resource for more specific troubleshooting related to its internal workings and features.
