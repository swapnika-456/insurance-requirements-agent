/// ==============================================================================
/// File: lib/core/api/endpoints.dart
/// Purpose: Centralized REST API endpoint constants and URI builders.
/// Architecture: Flutter Core Network Layer
/// ==============================================================================

class Endpoints {
  // In development, points to local FastAPI backend
  static const String baseUrl = 'http://localhost:8000/api/v1';

  // Document ingestion routes
  static const String uploadDocument = '$baseUrl/documents/upload';
  static String ingestSample(String type) => '$baseUrl/documents/sample/$type';
  static const String listDocuments = '$baseUrl/documents';
  static String getDocument(String id) => '$baseUrl/documents/$id';
  static String getDocumentChunks(String id) => '$baseUrl/documents/$id/chunks';
  static String deleteDocument(String id) => '$baseUrl/documents/$id';

  // Structured extraction routes
  static String extractProduct(String id) => '$baseUrl/extractions/$id';
  static String getExtraction(String id) => '$baseUrl/extractions/$id';

  // Requirements generation routes
  static String generateRequirements(String id) => '$baseUrl/requirements/$id/generate';
  static String getRequirements(String id) => '$baseUrl/requirements/$id';

  // Traceability routes
  static String getTraceabilityMatrix(String id) => '$baseUrl/traceability/$id';
  static String exportTraceabilityCsv(String id) => '$baseUrl/traceability/$id/export';

  // Review & Audit routes
  static String reviewItem(String id) => '$baseUrl/review/$id';
  static const String auditLogs = '$baseUrl/audit';
}
