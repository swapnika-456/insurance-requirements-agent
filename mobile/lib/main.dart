/// ==============================================================================
/// File: lib/main.dart
/// Purpose: Flutter application root entry point, ProviderScope initialization,
///          and MaterialApp.router wiring.
/// Architecture: Flutter Application Gateway
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: InsuranceRequirementsApp(),
    ),
  );
}

class InsuranceRequirementsApp extends StatelessWidget {
  const InsuranceRequirementsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Insurance Requirements Agent',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: appRouter,
    );
  }
}
