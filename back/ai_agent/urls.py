from django.urls import path
from . import views

urlpatterns = [
    path("ask/", views.ask, name="ai-agent-ask"),
    path("feedback/", views.feedback, name="ai-agent-feedback"),
    path("schema/", views.schema_info, name="ai-agent-schema"),
    path("schema/detail/", views.schema_detail, name="ai-agent-schema-detail"),
    path("table-data/", views.table_data, name="ai-agent-table-data"),
    path("refresh-schema/", views.refresh_schema, name="ai-agent-refresh-schema"),
    # Knowledge base CRUD
    path("knowledge/meta/", views.knowledge_meta, name="ai-agent-knowledge-meta"),
    path("knowledge/", views.knowledge_list, name="ai-agent-knowledge-list"),
    path("knowledge/<int:pk>/", views.knowledge_detail, name="ai-agent-knowledge-detail"),
    path("glossary/", views.glossary_list, name="ai-agent-glossary-list"),
    path("glossary/<int:pk>/", views.glossary_detail, name="ai-agent-glossary-detail"),
    path("rules/", views.rules_list, name="ai-agent-rules-list"),
    path("rules/<int:pk>/", views.rules_detail, name="ai-agent-rules-detail"),
]
