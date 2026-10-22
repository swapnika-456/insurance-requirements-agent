/// ==============================================================================
/// File: lib/features/product_detail/presentation/product_detail_screen.dart
/// Purpose: Interactive presentation of extracted insurance product parameters,
///          coverages, limits, rating factors, and verbatim citations.
/// Architecture: Flutter Features Layer / Product Extraction Presentation
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../shared/disclaimer_banner.dart';
import '../../../shared/citation_chip.dart';
import '../../../shared/status_badge.dart';
import '../../../shared/cost_indicator.dart';

final extractionProvider = FutureProvider.family.autoDispose<Map<String, dynamic>?, String>((ref, docId) async {
  final dio = ref.watch(dioProvider);
  try {
    final response = await dio.get(Endpoints.getExtraction(docId));
    return response.data as Map<String, dynamic>;
  } catch (e) {
    return null;
  }
});

class ProductDetailScreen extends ConsumerStatefulWidget {
  final String documentId;

  const ProductDetailScreen({super.key, required this.documentId});

  @override
  ConsumerState<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends ConsumerState<ProductDetailScreen> {
  bool _isExtracting = false;

  Future<void> _triggerExtraction() async {
    setState(() => _isExtracting = true);
    final dio = ref.read(dioProvider);
    try {
      await dio.post(Endpoints.extractProduct(widget.documentId));
      ref.invalidate(extractionProvider(widget.documentId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Extraction error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isExtracting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final extractAsync = ref.watch(extractionProvider(widget.documentId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Product Extraction & Citations', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(extractionProvider(widget.documentId)),
          ),
        ],
      ),
      body: Column(
        children: [
          const DisclaimerBanner(),
          Expanded(
            child: extractAsync.when(
              data: (data) {
                if (data == null) {
                  return _buildTriggerExtractionState();
                }
                return _buildExtractionContent(data);
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text('Error: $err')),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTriggerExtractionState() {
    return Center(
      child: Card(
        margin: const EdgeInsets.all(24),
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.psychology, size: 48, color: Color(0xFF0284C7)),
              const SizedBox(height: 16),
              const Text(
                'Product Extraction Pending',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Extract coverages, limits, deductibles, rating factors, and rules with clause grounding.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _isExtracting ? null : _triggerExtraction,
                icon: const Icon(Icons.play_arrow),
                label: Text(_isExtracting ? 'Extracting...' : 'Run Structured Extraction'),
              ),
              if (_isExtracting) ...[
                const SizedBox(height: 16),
                const LinearProgressIndicator(),
              ]
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildExtractionContent(Map<String, dynamic> res) {
    final status = res['status'] as String? ?? 'completed';
    final costUsd = (res['cost_usd'] as num?)?.toDouble() ?? 0.0;
    final totalTokens = (res['prompt_tokens'] as int? ?? 0) + (res['completion_tokens'] as int? ?? 0);
    final modelName = res['model_name'] as String? ?? 'gemini-2.5-flash';
    final product = res['data'] as Map<String, dynamic>;

    final coverages = (product['coverages'] as List<dynamic>?) ?? [];
    final deductibles = (product['deductibles'] as List<dynamic>?) ?? [];
    final ratingFactors = (product['rating_factors'] as List<dynamic>?) ?? [];
    final rules = (product['underwriting_rules'] as List<dynamic>?) ?? [];
    final exclusions = (product['exclusions'] as List<dynamic>?) ?? [];
    final endorsements = (product['endorsements'] as List<dynamic>?) ?? [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Action Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      StatusBadge(status: status),
                      const SizedBox(width: 10),
                      CostIndicator(totalTokens: totalTokens, costUsd: costUsd, modelName: modelName),
                    ],
                  ),
                  ElevatedButton.icon(
                    onPressed: () => context.go('/requirements/${widget.documentId}'),
                    icon: const Icon(Icons.assignment, size: 16),
                    label: const Text('View BRD & Stories'),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Product Header Card
              _buildProductHeaderCard(product),
              const SizedBox(height: 20),

              // Coverages & Limits
              _buildSectionTitle('1. Schedule of Coverages & Limits', Icons.shield),
              const SizedBox(height: 8),
              _buildCoveragesList(coverages),
              const SizedBox(height: 20),

              // Deductibles
              _buildSectionTitle('2. Deductible Schedule & Perils', Icons.monetization_on_outlined),
              const SizedBox(height: 8),
              _buildDeductiblesList(deductibles),
              const SizedBox(height: 20),

              // Actuarial Rating Factors
              _buildSectionTitle('3. Actuarial Rating Factors & Tiers', Icons.calculate_outlined),
              const SizedBox(height: 8),
              _buildRatingFactorsList(ratingFactors),
              const SizedBox(height: 20),

              // Underwriting & Eligibility Rules
              _buildSectionTitle('4. Underwriting Rules & Eligibility Gates', Icons.gavel_outlined),
              const SizedBox(height: 8),
              _buildUnderwritingRulesList(rules),
              const SizedBox(height: 20),

              // Exclusions & Endorsements
              _buildSectionTitle('5. Policy Exclusions & Optional Riders', Icons.block),
              const SizedBox(height: 8),
              _buildExclusionsAndEndorsements(exclusions, endorsements),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 18, color: const Color(0xFF1E3A8A)),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
        ),
      ],
    );
  }

  Widget _buildProductHeaderCard(Map<String, dynamic> p) {
    final prodName = p['product_name']?['value'] ?? 'Unknown Product';
    final lob = p['line_of_business']?['value'] ?? 'General Insurance';
    final state = p['state_or_jurisdiction']?['value'] ?? 'Statutory Standard';
    final effDate = p['effective_date']?['value'] ?? 'Not specified';

    final nameCitation = p['product_name']?['citation'];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    prodName,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                  ),
                ),
                if (nameCitation != null) _buildCitationWidget(nameCitation),
              ],
            ),
            const Divider(height: 20),
            Row(
              children: [
                _buildHeaderPill('Line of Business', lob, const Color(0xFF0284C7)),
                const SizedBox(width: 16),
                _buildHeaderPill('Jurisdiction', state, const Color(0xFF059669)),
                const SizedBox(width: 16),
                _buildHeaderPill('Effective Date', effDate, const Color(0xFF64748B)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeaderPill(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
        const SizedBox(height: 2),
        Text(value, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: color)),
      ],
    );
  }

  Widget _buildCoveragesList(List<dynamic> items) {
    if (items.isEmpty) return _buildNoItems('No coverages specified.');
    return Card(
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final c = items[i];
          final name = c['coverage_name'] ?? '';
          final limit = c['limit'] ?? '';
          final ded = c['deductible'] ?? 'None';
          final citation = c['citation'];

          return Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  flex: 3,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      const SizedBox(height: 2),
                      Text('Limit: $limit  |  Deductible: $ded', style: const TextStyle(fontSize: 12, color: Color(0xFF475569))),
                    ],
                  ),
                ),
                if (citation != null) _buildCitationWidget(citation),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildDeductiblesList(List<dynamic> items) {
    if (items.isEmpty) return _buildNoItems('No peril deductibles extracted.');
    return Card(
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final d = items[i];
          final peril = d['peril_or_coverage'] ?? '';
          final amount = d['amount_or_formula'] ?? '';
          final citation = d['citation'];

          return Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: Text('$peril:  $amount', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                ),
                if (citation != null) _buildCitationWidget(citation),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildRatingFactorsList(List<dynamic> items) {
    if (items.isEmpty) return _buildNoItems('No rating factors extracted.');
    return Card(
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final rf = items[i];
          final name = rf['factor_name'] ?? '';
          final code = rf['factor_code'] ?? '';
          final desc = rf['description_or_formula'] ?? '';
          final citation = rf['citation'];

          return Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(code.isNotEmpty ? '[$code] $name' : name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      const SizedBox(height: 2),
                      Text(desc, style: const TextStyle(fontSize: 12, color: Color(0xFF334155))),
                    ],
                  ),
                ),
                if (citation != null) _buildCitationWidget(citation),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildUnderwritingRulesList(List<dynamic> items) {
    if (items.isEmpty) return _buildNoItems('No underwriting rules extracted.');
    return Card(
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final r = items[i];
          final id = r['rule_id'] ?? '';
          final cond = r['condition'] ?? '';
          final action = r['underwriting_action'] ?? 'Refer';
          final citation = r['citation'];

          return Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('[$id] Action: ', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                          Text(action, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFFDC2626))),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(cond, style: const TextStyle(fontSize: 12, color: Color(0xFF334155))),
                    ],
                  ),
                ),
                if (citation != null) _buildCitationWidget(citation),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildExclusionsAndEndorsements(List<dynamic> exclusions, List<dynamic> endorsements) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Exclusions', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF991B1B))),
            const SizedBox(height: 6),
            ...exclusions.map((e) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text('• ${e['exclusion_title']}: ${e['description']}', style: const TextStyle(fontSize: 12)),
                  ),
                  if (e['citation'] != null) _buildCitationWidget(e['citation']),
                ],
              ),
            )),
            const Divider(height: 20),
            const Text('Endorsements & Riders', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF1E3A8A))),
            const SizedBox(height: 6),
            ...endorsements.map((en) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text('• [${en['endorsement_code']}] ${en['title']}: ${en['coverage_modification']}', style: const TextStyle(fontSize: 12)),
                  ),
                  if (en['citation'] != null) _buildCitationWidget(en['citation']),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildCitationWidget(dynamic c) {
    final page = c['page_number'] as int? ?? 1;
    final clause = c['clause_reference'] as String?;
    final quote = c['exact_quote'] as String? ?? 'Quoted from source policy';
    final conf = (c['confidence_score'] as num?)?.toDouble() ?? 1.0;
    final needsRev = c['needs_review'] as bool? ?? false;

    return CitationChip(
      pageNumber: page,
      clauseReference: clause,
      exactQuote: quote,
      confidenceScore: conf,
      needsReview: needsRev,
    );
  }

  Widget _buildNoItems(String msg) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Text(msg, style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8), fontStyle: FontStyle.italic)),
      ),
    );
  }
}
