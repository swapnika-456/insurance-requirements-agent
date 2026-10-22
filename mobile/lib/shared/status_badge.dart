/// ==============================================================================
/// File: lib/shared/status_badge.dart
/// Purpose: Status indicator pill for Draft, Approved, Rejected, and Needs Review items.
/// Architecture: Flutter Shared Presentation Component / Review Status
/// ==============================================================================

import 'package:flutter/material.dart';

class StatusBadge extends StatelessWidget {
  final String status;

  const StatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color text;
    IconData icon;

    switch (status.toLowerCase()) {
      case 'approved':
        bg = const Color(0xFFECFDF5);
        border = const Color(0xFFA7F3D0);
        text = const Color(0xFF065F46);
        icon = Icons.check_circle_outline;
        break;
      case 'rejected':
        bg = const Color(0xFFFFF1F2);
        border = const Color(0xFFFECDD3);
        text = const Color(0xFF9F1239);
        icon = Icons.cancel_outlined;
        break;
      case 'needs_review':
        bg = const Color(0xFFFFFBEB);
        border = const Color(0xFFFDE68A);
        text = const Color(0xFF92400E);
        icon = Icons.warning_amber_rounded;
        break;
      case 'draft':
      default:
        bg = const Color(0xFFF8FAFC);
        border = const Color(0xFFCBD5E1);
        text = const Color(0xFF475569);
        icon = Icons.edit_note;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: text),
          const SizedBox(width: 4),
          Text(
            status.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: text,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}
