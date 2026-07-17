import 'package:equatable/equatable.dart';

/// Domain entity representing an authenticated user. Framework-free by design.
class User extends Equatable {
  const User({
    required this.id,
    required this.email,
    this.fullName,
    this.isVerified = false,
  });

  final String id;
  final String email;
  final String? fullName;
  final bool isVerified;

  String get displayName =>
      (fullName != null && fullName!.trim().isNotEmpty) ? fullName! : email;

  @override
  List<Object?> get props => [id, email, fullName, isVerified];
}
