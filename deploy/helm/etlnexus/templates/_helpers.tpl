{{- define "etlnexus.fullname" -}}
{{- default .Release.Name .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "etlnexus.labels" -}}
app.kubernetes.io/name: etlnexus
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "etlnexus.selectorLabels" -}}
app.kubernetes.io/name: etlnexus
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
