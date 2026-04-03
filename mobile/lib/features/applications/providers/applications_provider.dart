import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';

class ApplicationsFilter {
  final String? status;
  final String? stage;
  final String? jobType;
  final double? minScore;
  final String? search;

  const ApplicationsFilter({
    this.status,
    this.stage,
    this.jobType,
    this.minScore,
    this.search,
  });
}

final applicationsProvider = FutureProvider.family<List<dynamic>, ApplicationsFilter>(
  (ref, filter) async {
    final api = ref.watch(apiClientProvider);
    return api.getApplications(
      status: filter.status,
      stage: filter.stage,
      jobType: filter.jobType,
      minScore: filter.minScore,
      search: filter.search,
    );
  },
);

final applicationDetailProvider = FutureProvider.family<Map<String, dynamic>, int>(
  (ref, id) async {
    final api = ref.watch(apiClientProvider);
    return api.getApplicationById(id);
  },
);
