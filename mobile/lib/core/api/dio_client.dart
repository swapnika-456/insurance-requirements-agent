/// ==============================================================================
/// File: lib/core/api/dio_client.dart
/// Purpose: Configured Dio HTTP client with interceptors and error diagnostics.
/// Architecture: Flutter Core Network Infrastructure
/// ==============================================================================

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'endpoints.dart';

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: Endpoints.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 45),
      headers: {
        'Accept': 'application/json',
      },
    ),
  );

  // Add logging interceptor for network observability
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        // In debug mode, logs outgoing endpoints
        return handler.next(options);
      },
      onResponse: (response, handler) {
        return handler.next(response);
      },
      onError: (DioException e, handler) {
        // Standardize server error formatting
        return handler.next(e);
      },
    ),
  );

  return dio;
});

class DioClient {
  static final Dio _dio = Dio(
    BaseOptions(
      baseUrl: Endpoints.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 45),
      headers: {'Accept': 'application/json'},
    ),
  );

  static Dio get instance => _dio;
}
