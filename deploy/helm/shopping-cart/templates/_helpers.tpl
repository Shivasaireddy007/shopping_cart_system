{{- define "shop.name" -}}{{ .Release.Name }}{{- end -}}

{{- define "shop.labels" -}}
app.kubernetes.io/part-of: shopping-cart
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "shop.selector" -}}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "shop.secretName" -}}
{{- if .Values.secrets.create -}}{{ include "shop.name" . }}-secrets{{- else -}}{{ .Values.secrets.existingSecret }}{{- end -}}
{{- end -}}

{{/* Settings shared by every container that runs the API image. */}}
{{- define "shop.appEnv" -}}
envFrom:
  - configMapRef:
      name: {{ include "shop.name" . }}-config
  - secretRef:
      name: {{ include "shop.secretName" . }}
{{- end -}}

{{- define "shop.podSecurity" -}}
automountServiceAccountToken: false
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
{{- end -}}

{{- define "shop.containerSecurity" -}}
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
{{- end -}}
