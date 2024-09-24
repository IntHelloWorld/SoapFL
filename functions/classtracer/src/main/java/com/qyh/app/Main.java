package com.qyh.app;

public class Main {

    public static class A {
        public void sayHello() {
            System.out.println("sayHello呀！");
        }
    }

    public static class B extends A {
        @Override
        public void sayHello() {
            System.out.println("sayHello呀！我是B");
        }
    }

    public static void main(String[] args) {
        System.out.println(add(122, 345));

        new A().sayHello();
        new B().sayHello();
    }

    public static int add(int a, int b) {
        return a + b;
    }

    public static int minus(int a, int b) {
        return a - b;
    }
}
