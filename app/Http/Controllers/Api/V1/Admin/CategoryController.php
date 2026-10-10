<?php

namespace App\Http\Controllers\Api\V1\Admin;

use App\Http\Controllers\Controller;
use App\Http\Resources\CategoryResource;
use App\Models\Category;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;

class CategoryController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate([
            'name' => ['required', 'string', 'max:255'],
            'slug' => ['sometimes', 'string', 'max:255', 'alpha_dash', 'unique:categories,slug'],
            'parent_id' => ['sometimes', 'nullable', 'integer', 'exists:categories,id'],
        ]);
        $data['slug'] ??= Str::slug($data['name']);

        abort_if(Category::where('slug', $data['slug'])->exists(), 422, 'A category with this slug already exists.');

        return (new CategoryResource(Category::create($data)))->response()->setStatusCode(201);
    }

    public function update(Request $request, Category $category): CategoryResource
    {
        $data = $request->validate([
            'name' => ['sometimes', 'string', 'max:255'],
            'slug' => ['sometimes', 'string', 'max:255', 'alpha_dash', Rule::unique('categories', 'slug')->ignore($category)],
            'parent_id' => ['sometimes', 'nullable', 'integer', 'exists:categories,id', Rule::notIn([$category->id])],
        ]);

        $category->update($data);

        return new CategoryResource($category);
    }

    public function destroy(Category $category): Response|JsonResponse
    {
        if ($category->products()->exists()) {
            return response()->json(['message' => 'Move or archive this category\'s products before deleting it.'], 409);
        }

        $category->delete();

        return response()->noContent();
    }
}
