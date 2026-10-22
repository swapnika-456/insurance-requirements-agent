/// ==============================================================================
/// File: test/widget_test.dart
/// Purpose: Widget tests for Flutter app startup, disclaimer banner rendering,
///          and initial navigation.
/// Architecture: Flutter Test Suite / Widget Tests
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:insurance_requirements_agent/main.dart';
import 'package:insurance_requirements_agent/shared/disclaimer_banner.dart';

void main() {
  testWidgets('App renders title, persistent disclaimer banner, and sample action cards', (WidgetTester tester) async {
    // Build our app and trigger a frame
    await tester.pumpWidget(
      const ProviderScope(
        child: InsuranceRequirementsApp(),
      ),
    );
    await tester.pumpAndSettle();

    // Verify app bar title
    expect(find.textContaining('Insurance Requirements Agent'), findsOneWidget);

    // Verify persistent AI disclaimer banner
    expect(find.byType(DisclaimerBanner), findsOneWidget);
    expect(find.textContaining('AI-GENERATED DRAFT OUTPUT'), findsOneWidget);

    // Verify sample upload options exist
    expect(find.textContaining('Auto Policy'), findsOneWidget);
    expect(find.textContaining('Homeowners'), findsOneWidget);
    expect(find.textContaining('Term Life'), findsOneWidget);
  });
}
