/// ==============================================================================
/// File: lib/core/router/app_router.dart
/// Purpose: Declarative GoRouter routing configuration for web and mobile.
/// Architecture: Flutter Core Navigation Infrastructure
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../features/upload/presentation/upload_screen.dart';
import '../../features/product_detail/presentation/product_detail_screen.dart';
import '../../features/requirements/presentation/requirements_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const UploadScreen(),
    ),
    GoRoute(
      path: '/product/:id',
      builder: (context, state) {
        final id = state.pathParameters['id']!;
        return ProductDetailScreen(documentId: id);
      },
    ),
    GoRoute(
      path: '/requirements/:id',
      builder: (context, state) {
        final id = state.pathParameters['id']!;
        return RequirementsScreen(documentId: id);
      },
    ),
  ],
);
