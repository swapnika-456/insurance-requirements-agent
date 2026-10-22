/// ==============================================================================
/// File: lib/shared/cost_indicator.dart
/// Purpose: Real-time token consumption and USD cost badge for executive visibility.
/// Architecture: Flutter Shared Presentation Component / Telemetry
/// ==============================================================================

import 'package:flutter/material.dart';

class CostIndicator extends StatelessWidget {
  final int totalTokens;
  final double costUsd;
  final String? modelName;

  const CostIndicator({
    super.key,
    required this.totalTokens,
    required this.costUsd,
    this.modelName,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4), // Emerald tint
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFBBF7D0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.bolt, size: 14, color: Color(0xFF16A34A)),
          const SizedBox(width: 4),
          Text(
            '$totalTokens tokens',
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF15803D)),
          ),
          const SizedBox(width: 6),
          Text(
            '|  \$${costUsd.toStringAsFixed(4)}',
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF166534)),
          ),
          if (modelName != null) ...[
            const SizedBox(width: 6),
            Text(
              '($modelName)',
              style: const TextStyle(fontSize: 10, color: Color(0xFF4ADE80)),
            ),
          ],
        ],
      ),
    );
  }
}
