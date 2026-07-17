import '../../domain/entities/user.dart';

/// Data-layer representation of a user, with JSON (de)serialisation.
class UserModel extends User {
  const UserModel({
    required super.id,
    required super.email,
    super.fullName,
    super.isVerified,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => UserModel(
        id: json['id'] as String,
        email: json['email'] as String,
        fullName: json['full_name'] as String?,
        isVerified: json['is_verified'] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'full_name': fullName,
        'is_verified': isVerified,
      };
}
