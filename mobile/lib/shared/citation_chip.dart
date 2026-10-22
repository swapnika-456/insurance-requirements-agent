/// ==============================================================================
/// File: lib/shared/citation_chip.dart
/// Purpose: Interactive citation badge displaying source page and clause,
///          triggering an inspection modal with exact quoted evidence on tap.
/// Architecture: Flutter Shared Presentation Component / Provenance UI
/// ==============================================================================

import 'package:flutter/material.dart';

class CitationChip extends StatelessWidget {
  final int pageNumber;
  final String? clauseReference;
  final String exactQuote;
  final double confidenceScore;
  final bool needsReview;

  const CitationChip({
    super.key,
    required this.pageNumber,
    this.clauseReference,
    required this.exactQuote,
    this.confidenceScore = 1.0,
    this.needsReview = false,
  });

  @override
  Widget build(BuildContext context) {
    final label = clauseReference != null
        ? 'P.$pageNumber • $clauseReference'
        : 'Page $pageNumber';

    final chipColor = needsReview ? Colors.amber.shade50 : const Color(0xFFEFF6FF);
    final borderColor = needsReview ? Colors.amber.shade400 : const Color(0xFFBFDBFE);
    final textColor = needsReview ? Colors.amber.shade900 : const Color(0xFF1D4ED8);

    return InkWell(
      onTap: () => _showCitationModal(context),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: chipColor,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: borderColor, width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              needsReview ? Icons.warning_amber_rounded : Icons.bookmark_border,
              size: 13,
              color: textColor,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: textColor,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showCitationModal(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          title: Row(
            children: [
              const Icon(Icons.verified, color: Color(0xFF0284C7), size: 22),
              const SizedBox(width: 8),
              const Text('Source Policy Citation', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildMetaRow('Source Page:', 'Page $pageNumber'),
              if (clauseReference != null)
                _buildMetaRow('Clause / Heading:', clauseReference!),
              _buildMetaRow(
                'Confidence Score:',
                '${(confidenceScore * 100).toInt()}% ${needsReview ? "(Needs Review)" : "(Verified)"}',
              ),
              const SizedBox(height: 12),
              const Text('Verbatim Policy Quote:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 6),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFFCBD5E1)),
                ),
                child: Text(
                  '"$exactQuote"',
                  style: const TextStyle(
                    fontStyle: FontStyle.italic,
                    fontSize: 12,
                    color: Color(0xFF1E293B),
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  Widget _buildMetaRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 125,
            child: Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), fontWeight: FontWeight.w500)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF0F172A))),
          ),
        ],
      ),
    );
  }
}
