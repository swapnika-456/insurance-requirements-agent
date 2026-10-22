/// ==============================================================================
/// File: lib/shared/disclaimer_banner.dart
/// Purpose: Persistent guardrail disclaimer widget displayed on all screens.
/// Architecture: Flutter Shared Presentation Component / Guardrails
/// ==============================================================================

import 'package:flutter/material.dart';

class DisclaimerBanner extends StatelessWidget {
  const DisclaimerBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: const Color(0xFFFEF3C7), // Light amber
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: Color(0xFFB45309), size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'AI-GENERATED DRAFT OUTPUT — All generated artifacts (BRDs, stories, data models) require human review and sign-off before implementation.',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: Colors.amber.shade900,
                letterSpacing: 0.2,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
